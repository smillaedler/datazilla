/*******
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/.
 * *****/
var PerformanceGraphComponent = new Class({

    Extends: Component,

    jQuery:'PerformanceGraphComponent',

    initialize: function(selector, options){

        this.setOptions(options);

        this.parent(options);

        this.view = new PerformanceGraphView();
        this.model = new PerformanceGraphModel();

        this.appToggleEvent = 'APP_TOGGLE_EV';
        this.testToggleEvent = 'TEST_TOGGLE_EV';
        this.perfPlotClickEvent = 'PERF_PLOT_CLICK_EV';

        this.testData = {};
        this.appData = {}
        this.chartData = {};
        this.seriesIndexDataMap = {};
        this.tickDisplayDates = {};
        this.checkedApps = {};
        this.data = {};

        this.replicatesInitialized = false;

        this.chartOptions = {
            'grid': {
                'clickable': true,
                'hoverable': true,
                'autoHighlight': true,
                'color': '#B6B6B6',
                'borderWidth': 0.5
            },

            'xaxis': {
                'tickFormatter': _.bind(this.formatLabel, this)
            },

            'yaxis': {
                'autoscaleMargin':0.3
            },

            'series': {

                'points': {
                    'radius': 2.5
                }
            },

            'selection':{
                'mode':'x',
                'color':'#BDBDBD'
            },

            'hooks': {
                'draw':[this.draw]
            } };

        $(this.view.appContainerSel).bind(
            this.appToggleEvent, _.bind( this.appToggle, this )
            );

        $(this.view.appContainerSel).bind(
            this.testToggleEvent, _.bind( this.testToggle, this )
            );

        $(this.view.chartContainerSel).bind(
            'plotclick', _.bind(this._clickPlot, this)
            );

        $(this.view.chartContainerSel).bind(
            'plothover', _.bind(this._hoverPlot, this)
            );

        $(this.view.timeRangeSel).bind(
            'change', _.bind(this.changeTimeRange, this)
            );

        $(this.view.branchSel).bind(
            'change', _.bind(this.changeTimeRange, this)
            );
    },
    formatLabel: function(label, series){
        return this.tickDisplayDates[label] || "";
    },
    changeTimeRange: function(event){
        this.testToggle(event, this.testData);
    },
    appToggle: function(event, data){

        if(this.checkedApps[ data['test_id'] ]){

            this.checkedApps[ data['test_id'] ] = false;

        }else{

            this.checkedApps[ data['test_id'] ] = true;

        }

        if(this.data){
            this.renderPlot(this.data);
        }

    },
    testToggle: function(event, data){

        this.testData = data;

        this.view.setGraphTestName(this.testData.url);

        var testIds = _.keys(data.test_ids);

        var range = $(this.view.timeRangeSel).val();
        var branch = $(this.view.branchSel).val();

        this.view.hideData();

        this.model.getAppData(
            this, this.renderPlot, testIds.join(','), data.url, range,
            branch
            );
    },
    renderPlot: function(data){

        this.data = data;

        this.chartData = {};

        var i = 0;

        var testId = 0;
        var appColor = "";
        var appName = "";
        var timestamp = "";
        var formattedTime = "";

        for(i = 0; i<data.length; i++){

            testId = data[i]['test_id'];

            appName = this.testData['test_ids'][testId]['name'];
            appColor = this.testData['test_ids'][testId]['color'];

            if(!this.chartData[ testId ]){
                this.chartData[ testId ] = {};
                this.chartData[ testId ][ 'id' ] = testId;
                this.chartData[ testId ][ 'name' ] = appName;
                this.chartData[ testId ][ 'color' ] = appColor;
                this.chartData[ testId ][ 'background_color' ] = this.view.hexToRgb(appColor);
                this.chartData[ testId ][ 'points' ] = { 'show': true };
                this.chartData[ testId ][ 'lines' ] = { 'show': true };
                this.chartData[ testId ][ 'data' ] = [];
                this.chartData[ testId ][ 'full_data' ] = [];
            }

            timestamp = data[i]['date_run'];

            //Don't add x-axis labels to the first and last x-axis values
            if((i > 0) && (i < data.length - 1)){
                if(!this.tickDisplayDates[ data[i]['test_run_id'] ]){
                    formattedTime = this.view.convertTimestampToDate(timestamp);
                    this.tickDisplayDates[ data[i]['test_run_id'] ] = formattedTime;
                }
            }

            if(!data[i]['formatted_date_run']){
                data[i]['formatted_date_run'] = this.view.convertTimestampToDate(
                    timestamp, true
                    );
            }

            //Data for flot
            this.chartData[ testId ][ 'data' ].push(
                [ data[i]['test_run_id'], data[i]['avg'] ]
                );

            //Data for presentation
            this.chartData[ testId ][ 'full_data' ].push(
                [ data[i] ]
                );
        }

        var chart = [];
        var testIds = _.keys(this.chartData);

        var j = 0;
        var seriesIndex = 0;

        this.seriesIndexDataMap = {};

        for(j = 0; j<testIds.length; j++){

            if(this.checkedApps && !this.checkedApps[ testIds[j] ]){
                continue;
            }

            seriesIndex = chart.push( this.chartData[ testIds[j] ] ) - 1
            this.seriesIndexDataMap[seriesIndex] = this.chartData[ testIds[j] ];
        }

        this.view.showData();

        this.plot = $.plot(
            $(this.view.chartContainerSel),
            chart,
            this.chartOptions
            );

        if(!this.replicatesInitialized && this.seriesIndexDataMap[seriesIndex]){
            this._clickPlot({}, {}, { 'seriesIndex':seriesIndex, 'dataIndex':0 });
            this.view.resetSeriesLabelBackground(this.chartData);
            this.replicatesInitialized = true;
        }
    },
    _clickPlot: function(event, pos, item){
        var seriesDatum = this.seriesIndexDataMap[ item.seriesIndex ];
        var datapointDatum = this.seriesIndexDataMap[ item.seriesIndex ]['full_data'][ item.dataIndex ];

        this.plot.unhighlight();
        this.plot.highlight(item.seriesIndex, item.dataIndex);

        this._hoverPlot(event, pos, item);

        datapointDatum[0]['branch'] = $(this.view.branchSel).val();

        $(this.view.appContainerSel).trigger(
            this.perfPlotClickEvent,
            { 'series':seriesDatum, 'datapoint':datapointDatum[0] }
            );
    },
    _hoverPlot: function(event, pos, item){

        this.view.resetSeriesLabelBackground(this.chartData);

        if(!_.isEmpty(item)){
            var seriesDatum = this.seriesIndexDataMap[ item.seriesIndex ];
            var datapointDatum = this.seriesIndexDataMap[ item.seriesIndex ]['full_data'][ item.dataIndex ];
            this.view.setDetailContainer(seriesDatum, datapointDatum[0]);
            this.view.highlightSeriesLabel(seriesDatum);
        }
    }
});
var PerformanceGraphView = new Class({

    Extends:View,

    jQuery:'PerformanceGraphView',

    initialize: function(selector, options){

        this.setOptions(options);

        this.parent(options);

        this.appContainerSel = '#app_container';

        this.timeRangeSel = '#app_time_range';
        this.branchSel = '#app_branch';
        this.chartContainerSel = '#app_perf_chart';
        this.appTestName = '#app_test_name';
        this.graphDetailContainerSel = '#app_perf_detail_container';
        this.perfDataContainerSel = '#app_perf_data_container';
        this.perfWaitSel = '#app_perf_wait';

        this.detailIdPrefix = 'app_series_';
        this.idFields = [
            'revision', 'formatted_date_run', 'avg', 'std', 'min', 'max'
            ];
        this.appDetailIdSel = '#' + this.detailIdPrefix + 'application';

        this.appSeriesIdPrefix = 'app_series_';

    },
    showData: function(){
        $(this.perfWaitSel).css('display', 'none');
        $(this.perfDataContainerSel).css('display', 'block');

    },
    hideData: function(){
        $(this.perfDataContainerSel).css('display', 'none');
        $(this.perfWaitSel).css('display', 'block');
    },
    highlightSeriesLabel: function(seriesDatum){
        $('#' + this.appSeriesIdPrefix + seriesDatum.id ).css(
            'background-color', 'white'
            );
    },
    resetSeriesLabelBackground: function(chartData){
        var testId = 0;
        for(testId in chartData){
            $('#' + this.appSeriesIdPrefix + testId ).css(
                'background-color', chartData[ testId ][ 'background_color' ]
                );
        }
    },
    setGraphTestName: function(name){
        $(this.appTestName).text(name);
    },
    setDetailContainer: function(seriesDatum, datapointDatum){

        $(this.graphDetailContainerSel).css(
            'background-color', seriesDatum.background_color
            );
        $(this.graphDetailContainerSel).css(
            'border-color', seriesDatum.color
            );
        $(this.graphDetailContainerSel).css(
            'border-width', 1
            );

        $(this.appDetailIdSel).text( seriesDatum['name'] );
        var i = 0;
        var fieldName = "";
        var idSel = "";
        var value = "";

        for(i = 0; i<this.idFields.length; i++){
            fieldName = this.idFields[i];
            idSel = '#' + this.detailIdPrefix + fieldName;

            value = datapointDatum[fieldName];
            if(fieldName === 'revision'){
                value = APPS_PAGE.getRevisionSlice(
                    datapointDatum[fieldName]
                    );
                $(idSel).attr('title', datapointDatum[fieldName]);
                $(idSel).attr('href', APPS_PAGE.gaiaHrefBase + value);
            }

            $(idSel).text( datapointDatum[fieldName] );
        }
    }
});
var PerformanceGraphModel = new Class({

    Extends:Model,

    jQuery:'PerformanceGraphModel',

    initialize: function(options){

        this.setOptions(options);

        this.parent(options);

    },

    getAppData: function(context, fnSuccess, testIds, pageName, range, branch){

        var uri = '/' + APPS_PAGE.refData.project + '/testdata/test_values?' + 
            'branch=BRANCH&test_ids=TEST_IDS&page_name=PAGE_NAME&range=RANGE';

        uri = uri.replace('BRANCH', branch);
        uri = uri.replace('TEST_IDS', testIds);
        uri = uri.replace('PAGE_NAME', pageName);
        uri = uri.replace('RANGE', range);

        jQuery.ajax( uri, {
            accepts:'application/json',
            dataType:'json',
            cache:false,
            type:'GET',
            data:data,
            context:context,
            success:fnSuccess,
        });
    }
});
from optparse import make_option
from random import randint
from django.conf import LazySettings

from base import ProjectBatchCommand
from datazilla.util.cnv import CNV
from datazilla.util.map import Map
from datazilla.util.db import DB
from datazilla.util.debug import D


from datazilla.daemons.alert import send_alerts
from datazilla.model.utils import datazilla


class Command(ProjectBatchCommand):

    LOCK_FILE = "run_metrics"+str(randint(100000000, 999999999))

    help = "Run alert methods."

    option_list = ProjectBatchCommand.option_list + (
        make_option('--debug',
                    action='store_true',
                    dest='debug',
                    default=None,
                    help=('Send stuff to stdout')
        ),
        make_option('--settings_file',
            action='store',
            dest='settings_file',
            default=None,
            help=('JSON file with settings')
        ),
        )


    def handle_project(self, project, **options):

        with open(options["settings_file"]) as f:
            settings=CNV.JSON2object(f.read())
            
        try:
            D.println("Running alert for project ${project}", {"project":project})

            with DB(settings.database) as db:
                send_alerts(
                    db=db,
                    debug=options.get('debug') or datazilla.settings.DEBUG
                )
        except Exception, e:
            D.warning("Failure to run alerts", cause=e)



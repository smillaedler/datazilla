import argparse
from optparse import make_option
from random import randint


from base import ProjectBatchCommand
from datazilla.daemons.alert_exception import exception_point
from datazilla.util.cnv import CNV
from datazilla.util.db import DB
from datazilla.util.debug import D



class Command(ProjectBatchCommand):

    LOCK_FILE = "run_metrics"+str(randint(100000000, 999999999))

    help = "Run alert_exception methods."


    option_list = ProjectBatchCommand.option_list + (
        make_option('--debug',
                    action='store_true',
                    dest='debug',
                    default=False,
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
                exception_point(
                    db=db,
                    debug=options.get('debug') or (settings.debug is not None),
                )
        except Exception, e:
            D.warning("Failure to run alerts", cause=e)



from optparse import make_option
from random import randint


from base import ProjectBatchCommand
from datazilla.daemons.alert_threshold import page_threshold_limit
from datazilla.model.metrics2 import DataSource
from datazilla.util.bunch import Bunch
from datazilla.util.debug import D
from datazilla.model.utils import datazilla


class Command(ProjectBatchCommand):

    LOCK_FILE = "run_metrics"+str(randint(100000000, 999999999))

    help = "Run alert_threashold methods."

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
                    help=('file with connection info, and other config options')
        ),
        )


    def handle_project(self, project, **options):

        try:
            D.println("Running alert for project ${project}", {"project":project})

            db=DataSource(project=project)

            page_threshold_limit(Bunch({
                "db":db,
                "debug":options.get('debug') or datazilla.settings.DEBUG
            }))
        except Exception, e:
            D.warning("Failure to run alerts", cause=e)



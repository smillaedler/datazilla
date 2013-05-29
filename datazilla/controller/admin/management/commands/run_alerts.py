from optparse import make_option


from base import ProjectBatchCommand
from datazilla.model.util.bunch import Bunch
from datazilla.model.util.db import getDatabaseConnection
from datazilla.model.util.debug import D


from datazilla.controller.admin.alert import send_alerts


class Command(ProjectBatchCommand):

#    LOCK_FILE = "run_metrics"

    help = "Run alert methods."

    option_list = ProjectBatchCommand.option_list + (
        make_option('--debug',
                    action='store_true',
                    dest='debug',
                    default=None,
                    help=('Send stuff to stdout')
        ),
        )


    def handle_project(self, project, **options):
        D.println("Running alert for project ${project}", {"project":project})

        send_alerts(Bunch({
            "db":getDatabaseConnection(project, "perftest"),
            "debug":options.get('debug')
        }))




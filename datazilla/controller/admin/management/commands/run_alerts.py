from optparse import make_option


from base import ProjectBatchCommand
from model.util.Bunch import Bunch
from model.util.Debug import D
from controller.admin import alert
from model.utils import getDatabaseConnection


class Command(ProjectBatchCommand):

    LOCK_FILE = "run_metrics"

    help = "Run alert methods."

    option_list = ProjectBatchCommand.option_list + (
        make_option('--debug',
                    action='store_true',
                    dest='debug',
                    default=None,
                    help=('Send stuff to stdout')
        ))


    def handle_project(self, project, **options):
        D.println("Running alert for project ${project}", {"project":project})

        alert.send_alerts(Bunch({
            "db":getDatabaseConnection(project, "perftest"),
            "debug":options.get('debug')
        }))




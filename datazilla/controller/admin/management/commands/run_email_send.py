from optparse import make_option
from random import randint

from base import ProjectBatchCommand
from datazilla.daemons.email_send import email_send
from datazilla.util.map import Map
from datazilla.util.cnv import CNV
from datazilla.util.db import get_database_connection
from datazilla.util.debug import D
from datazilla.model.utils import nvl


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
            D.println("Running email for project ${project}", {"project":project})

            email_send(Map(
                db=get_database_connection(settings.database),
                debug=options.get('debug') or (settings.debug is not None),
                settings=settings
            ))
        except Exception, e:
            D.warning("Failure to run alerts", cause=e)



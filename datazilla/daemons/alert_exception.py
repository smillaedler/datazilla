from datetime import timedelta, datetime
from model.utils import get_database_connection, error, nvl


##find single points that deviate from the trend
def exception_point (env):
    assert env.db is not None


    #LOAD CONFIG

    #CALCULATE HOW FAR BACK TO LOOK
    #BRING IN ALL NEEDED DATA
    #FOR EACH PAGE
        #ROLL THROUGH SERIES LOOKING FOR EXCEPTIONS THAT DEVIATE GREATLY
        #CHECK IF ALREADY AN ALERT
            #IF SO, UPDATE
            #IF NOT, ADD
    pass




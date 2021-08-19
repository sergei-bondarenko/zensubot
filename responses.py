import random

from database import db_query


class Responses:
    """Class to save responses in memory on each start of the bot. This is done to remove extensive database querying"""

    responses = dict()

    @classmethod
    def collect(cls):
        #Done on startup
        data = db_query("select job_type, response_type, phrase from responses")
        for job_type, response_type, text in data:
            cls.responses[(job_type, response_type)] = text

    @classmethod
    def get(cls, job_type: int, response_type: int) -> str:
        #Gets random response if it exists or returns empty string otherwise
        try:
            text = cls.responses[(job_type, response_type)]
            phrases = [x.strip() for x in text.split("\n") if len(x) != 1]

            #zero len list breaks random choice
            if len(phrases) == 0:
                phrases = ['']
            return random.choice(phrases)
        except KeyError:
            return ""

    @classmethod
    def get_entity(cls, job_type: int, response_type: int) -> str:
        #Gets random response if it exists or returns empty string otherwise
        try:
            return cls.responses[(job_type, response_type)]
        except KeyError:
            return ""

    @classmethod
    def update(cls, job_type: int, response_type: int, text: str) -> None:
        #Runs after insertion of new responses to database
        cls.responses[(job_type, response_type)] = text
    
    def delete(cls, job_type: int, response_type: int) -> None:
        del cls.responses[(job_type, response_type)]

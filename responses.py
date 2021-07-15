import random

from database import db_query


class Responses:
    responses = dict()

    @classmethod
    def collect(cls):
        data = db_query("select job_type, response_type, phrase from responses")
        for job_type, response_type, text in data:
            cls.responses[job_type] = {response_type: text}

    @classmethod
    def get(cls, job_type, response_type):
        try:
            text = cls.responses[job_type][response_type]
            phrases = [x.strip() for x in text.split("\n") if len(x)!= 1]
            return random.choice(phrases)
        except KeyError:
            return None
    
    @classmethod
    def update(cls, job_type, response_type, text):
        cls.responses[job_type] = {response_type: text}

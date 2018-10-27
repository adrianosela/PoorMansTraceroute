FROM python:3

ADD myTraceRoute.py /

CMD [ "python", "myTraceRoute.py", "google.com" ]

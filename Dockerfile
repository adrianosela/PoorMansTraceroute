FROM python:3

ADD traceroute.py /

CMD [ "python", "traceroute.py", "google.com" ]

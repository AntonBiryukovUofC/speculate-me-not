FROM python:3.10
RUN apt-get update && apt-get -y install cron
COPY requirements.txt /opt/app/requirements.txt
RUN pip install -r /opt/app/requirements.txt
COPY cron-spec /etc/cron.d/cron-spec
# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/cron-spec
# Apply cron job
RUN crontab /etc/cron.d/cron-spec
# Create the log file to be able to run tail
RUN touch /var/log/cron.log
# Run the command on container startup
COPY . /opt/app
# install punkt with nltk
RUN python -m nltk.downloader punkt
ENTRYPOINT ["sh", "/opt/app/entrypoint.sh"]
#CMD ["cron", "-f"]


FROM python:3.7.9 as base

FROM base as builder

RUN mkdir /install
RUN /bin/sh -c 'apt-get update'
COPY requirements.txt /install/requirements.txt
RUN /bin/sh -c 'pip3 install --no-cache-dir --upgrade pip'
RUN /bin/sh -c 'pip3 install --no-warn-script-location --no-cache-dir --prefix /install -r /install/requirements.txt'

FROM base

# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1

COPY --from=builder /install /usr/local

WORKDIR /app
RUN mkdir /app/staticfiles
RUN mkdir /app/mediafiles

# copy project files on /app folder
COPY . .

EXPOSE 8000
ENTRYPOINT ["/bin/sh", "docker/entrypoint.sh"]
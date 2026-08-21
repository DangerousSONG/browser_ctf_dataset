FROM ubuntu:24.04

RUN apt update && apt install -y \
    python3 \
    python3-pip \
    socat

RUN useradd -m ctf

WORKDIR /home/ctf

RUN chown root:root /home/ctf && chmod 755 /home/ctf

COPY ./share/d8 /home/ctf/
COPY ./share/run.sh /home/ctf/
COPY ./share/server.py /home/ctf/

COPY ./readflag /
COPY ./flag_1 /
COPY ./flag_2 /flag

RUN mv /flag_1 /$(head /dev/urandom| md5sum | awk '{print $1".txt"}')
RUN chmod 400 /flag && chmod 755 /readflag && chmod +x /readflag && chmod +s /readflag

USER ctf

CMD ["/home/ctf/run.sh"]

EXPOSE 7000
import click

from . import register_parser

from . import NTFYClientRealTime

@click.group
def cli():
    pass

server_hostname_option = \
        click.option("--server-hostname",
                     envvar="NTFY_SERVER_HOSTNAME")
topic_option = \
        click.option("--topic",
                     envvar="NTFY_TOPIC")
token_option = \
        click.option("--token",
                     envvar="NTFY_TOKEN")

@cli.command()
@server_hostname_option
@topic_option
@token_option
def json(server_hostname, topic, token):
    @register_parser
    def return_json(raw_data):
        import json
        json_notification = json.dumps(raw_data)

        print(json_notification)

        #return json_notification

    #  client = NTFYClientRealTime()
    client = NTFYClientRealTime(server_hostname, topic, token)
    client.run_forever()


if __name__ == "__main__":

    cli()


#!/usr/bin/env python3

from aiohttp import web, request
import aiohttp
import asyncio
import boto3
import base64
import http
import logging
import json
import os

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(filename)s:%(lineno)3d %(message)s',
                    datefmt='%d-%m-%Y:%H:%M:%S')

routes = web.RouteTableDef()

session = boto3.session.Session()
ec2_client = session.client(
    service_name='ec2',
    aws_access_key_id='aaa',
    aws_secret_access_key='bbb',
    endpoint_url='http://localstack:4597',
)

ec2_instances = {}

async def start_background_tasks(app):
    app['token_task'] = app.loop.create_task(loop_ec2_info(app))


async def loop_ec2_info(app):
    global ec2_instances


    while True:
        await asyncio.sleep(10)
        try:
            logging.error("Requesting aws info")
            ec2_instances = ec2_client.describe_instances()
        except:
            logging.error("FailedRequesting aws info")



async def create_client_session(app):
    conn = aiohttp.TCPConnector(loop=app.loop, use_dns_cache=True, ttl_dns_cache=10, enable_cleanup_closed=True)
    app['session'] = aiohttp.ClientSession(connector=conn)

async def default_handler(request):
    return web.Response(status=http.HTTPStatus.BAD_REQUEST,
                        text="very bad request")

@routes.get('/health')
async def health_handler(request):
    logging.info('healthcheck')
    status = http.HTTPStatus.OK
    return web.Response(status=status.value,
                        text=status.name,
                        headers={'Access-Control-Allow-Origin': '*'})

@routes.get('/info')
async def health_handler(request):
    logging.info('/info')
    status = http.HTTPStatus.OK
    return web.Response(status=status.value,
                        text=str(ec2_instances),
                        headers={'Access-Control-Allow-Origin': '*'})


app = web.Application()
app.add_routes(routes)
app.router.add_route('*', '/', default_handler)

app.on_startup.append(lambda app: start_background_tasks(app))
app.on_startup.append(create_client_session)

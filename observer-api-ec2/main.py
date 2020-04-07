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
from itertools import islice

from random import randrange

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'local')

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(filename)s:%(lineno)3d %(message)s',
                        datefmt='%d-%m-%Y:%H:%M:%S',
                        level=logging._nameToLevel[LOG_LEVEL])

routes = web.RouteTableDef()

session = boto3.session.Session()
ec2_client = session.client(
    service_name='ec2',
    aws_access_key_id='aaa',
    aws_secret_access_key='bbb',
    endpoint_url='http://localstack:4597',
)

reservations = {}
ec2_instances_info = {}

async def start_background_tasks(app):
    app['loop_ec2_describe_instances'] = app.loop.create_task(loop_ec2_describe_instances(app))
    app['loop_ec2_get_instances_info'] = app.loop.create_task(loop_ec2_get_instances_info(app))

async def loop_ec2_describe_instances(app):
    global reservations

    while True:
        await asyncio.sleep(10)
        try:
            logging.info("Requesting aws info")
            reservations = ec2_client.describe_instances()
        except:
            logging.error("Failed Requesting aws info")


async def loop_ec2_get_instances_info(app):
    global reservations
    global ec2_instances_info

    while True:
        await asyncio.sleep(5)
        try:
            ec2_instances = {}
            logging.info("Refreshing instance info map")
            for reservation in reservations['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    instance_cpu_cores = 2 # ec2_client.describe_instance_types(InstanceTypes=["c3.8xlarge"])
                    instance_cpu_threads = 2
                    instance_cpu_mhz = 2400
                    instance_cpu_load = randrange(100)
                    cpu_available_points = ( 1 - instance_cpu_load * 0.01 ) * instance_cpu_cores * instance_cpu_mhz
                    ec2_instances[instance_id] = {'InstanceType': instance_type,
                                                       'cpu_cores': instance_cpu_cores,
                                                       'cpu_threads': instance_cpu_threads,
                                                       'cpu_mhz': instance_cpu_mhz,
                                                       'cpu_load': instance_cpu_load,
                                                       'cpu_available_points': cpu_available_points }
            ec2_instances_info = ec2_instances
        except:
            logging.info("Failed Requesting aws instances info")



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


@routes.get('/reservations')
async def reservations_handler(request):
    logging.info('/info')
    status = http.HTTPStatus.OK
    return web.Response(status=status.value,
                        text=str(reservations),
                        headers={'Access-Control-Allow-Origin': '*'})

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))

@routes.get('/instances')
async def instances_handler(request):
    global ec2_instances_info

    logging.info('/instances')

    params = request.rel_url.query

    if 'available' in params.keys():
        n = int(params['available'])
        message = take(n, sorted(ec2_instances_info.items(), key=lambda x: x[1]['cpu_available_points'], reverse=True))

    elif 'busy' in params.keys():
        n = int(params['busy'])
        message = take(n, sorted(ec2_instances_info.items(), key=lambda x: x[1]['cpu_available_points']))

    else:
        message = ec2_instances_info

    status = http.HTTPStatus.OK
    return web.Response(status=status.value,
                        text=json.dumps(message),
                        headers={'Access-Control-Allow-Origin': '*'})


app = web.Application()
app.add_routes(routes)
app.router.add_route('*', '/', default_handler)

app.on_startup.append(lambda app: start_background_tasks(app))
app.on_startup.append(create_client_session)

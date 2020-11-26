#========================================================#
#                                                        #
#  VP-clerk: cloudtasks.py - Cloud Tasks 接続クラス     　 #
#                                                        #
#                            (C) 2019-2019 VIPPOOL Inc.  #
#                                                        #
#========================================================#

import os
import config
from google.cloud import tasks_v2
from google.cloud.tasks_v2.services.cloud_tasks.transports import CloudTasksGrpcTransport
import grpc

def CloudTasksClient():
    if os.getenv('SERVER_SOFTWARE', '').startswith('Google App Engine/'):
        return tasks_v2.CloudTasksClient()
    else:
        # ローカル環境等にエミュレータが存在する場合を想定
        # grpc.insecure_channel()により接続するので注意
        cloud_tasks_emulator_host = os.getenv('CLOUD_TASKS_EMULATOR_HOST')

        return tasks_v2.CloudTasksClient(
            transport=CloudTasksGrpcTransport(channel=grpc.insecure_channel(cloud_tasks_emulator_host))
        )

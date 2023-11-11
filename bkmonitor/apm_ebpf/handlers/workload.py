# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云 - 监控平台 (BlueKing - Monitor) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import typing
from dataclasses import asdict, dataclass

from dacite import from_dict
from django.utils.datetime_safe import datetime

from apm_ebpf.apps import logger
from apm_ebpf.constants import WorkloadType
from apm_ebpf.models.workload import DeepflowWorkload


@dataclass
class _BaseContent:
    name: str
    is_normal: bool
    workload_type: WorkloadType


@dataclass
class _DeploymentSpecPort:

    name: str
    containerPort: int
    protocol: str


@dataclass
class DeploymentContent(_BaseContent):
    replicas: int = None
    image: str = None
    image_name: str = None
    ports: typing.List[_DeploymentSpecPort] = None

    workload_type: WorkloadType = WorkloadType.DEPLOYMENT.value


@dataclass
class _ServicePort:
    name: str
    port: int
    target_port: int
    protocol: typing.Union[str, None]
    node_port: typing.Union[int, None]


@dataclass
class ServiceContent(_BaseContent):
    ports: typing.List[_ServicePort] = None
    type: str = None
    workload_type: str = WorkloadType.SERVICE.value


class WorkloadContent:

    _normal_predicate = {
        WorkloadType.DEPLOYMENT.value: lambda i: any(
            True for j in i.conditions if j.type == "Available" and j.status == "True"
        )
    }

    @classmethod
    def deployment_to(cls, describe) -> DeploymentContent:
        spec_describe = describe.spec
        image = spec_describe.template.spec.containers[0]

        status_describe = describe.status

        return DeploymentContent(
            name=describe.metadata.name,
            replicas=spec_describe.replicas,
            image=image.image,
            image_name=image.name,
            ports=[
                _DeploymentSpecPort(name=i.name, containerPort=i.container_port, protocol=i.protocol)
                for i in image.ports
            ],
            is_normal=cls._normal_predicate[WorkloadType.DEPLOYMENT.value](status_describe),
        )

    @classmethod
    def service_to(cls, describe) -> ServiceContent:
        spec_describe = describe.spec

        return ServiceContent(
            name=describe.metadata.name,
            ports=[
                _ServicePort(
                    name=i.name,
                    port=i.port,
                    node_port=i.node_port,
                    target_port=i.target_port,
                    protocol=i.protocol,
                )
                for i in spec_describe.ports
            ],
            type=describe.spec.type,
            is_normal=True,
        )

    @classmethod
    def extra_port(cls, content, name) -> int:
        """
        从NodePort Service定义中提取指定名称的端口号
        """
        service = from_dict(ServiceContent, content)

        if service.type != "NodePort":
            logger.warning(f"service: {service.name} does not match support type({service.type}) NodePort.")
            return 0

        for port in service.ports:
            if port.name == name:
                return port.node_port

        return 0


class WorkloadHandler:
    def __init__(self, bk_biz_id, cluster_id):
        self.bk_biz_id = bk_biz_id
        self.cluster_id = cluster_id

    def upsert(self, namespace, content: _BaseContent):
        params = {
            "bk_biz_id": self.bk_biz_id,
            "cluster_id": self.cluster_id,
            "namespace": namespace,
            "name": content.name,
            "type": content.workload_type,
        }
        record = DeepflowWorkload.objects.filter(**params).first()
        if record:
            record.content = asdict(content)
            record.is_normal = content.is_normal
            record.last_check_time = datetime.now()
            record.save()
        else:
            DeepflowWorkload.objects.create(
                bk_biz_id=self.bk_biz_id,
                cluster_id=self.cluster_id,
                namespace=namespace,
                name=content.name,
                content=asdict(content),
                type=content.workload_type,
                is_normal=content.is_normal,
                last_check_time=datetime.now(),
            )

    @classmethod
    def list_deployments(cls, bk_biz_id, namespace):
        return DeepflowWorkload.objects.filter(
            bk_biz_id=bk_biz_id, namespace=namespace, type=WorkloadType.DEPLOYMENT.value
        )

    @classmethod
    def list_services(cls, bk_biz_id, namespace, cluster_id):
        return DeepflowWorkload.objects.filter(
            bk_biz_id=bk_biz_id, cluster_id=cluster_id, namespace=namespace, type=WorkloadType.SERVICE.value
        )
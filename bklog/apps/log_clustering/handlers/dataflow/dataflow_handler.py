# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making BK-LOG 蓝鲸日志平台 available.
Copyright (C) 2021 THL A29 Limited, a Tencent company.  All rights reserved.
BK-LOG 蓝鲸日志平台 is licensed under the MIT License.
License for BK-LOG 蓝鲸日志平台:
--------------------------------------------------------------------
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial
portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
We undertake not to change the open source license (MIT license) applicable to the current version of
the project delivered to anyone in the future.
"""
import copy
import json
import os
from dataclasses import asdict

import arrow
from django.conf import settings
from django.utils.translation import ugettext as _
from jinja2 import Environment, FileSystemLoader
from retrying import retry

from apps.api import BkDataAIOPSApi, BkDataDatabusApi, BkDataDataFlowApi, BkDataMetaApi
from apps.api.base import DataApiRetryClass, check_result_is_true
from apps.log_clustering.constants import (
    AGGS_FIELD_PREFIX,
    DEFAULT_NEW_CLS_HOURS,
    MAX_FAILED_REQUEST_RETRY,
    NOT_NEED_EDIT_NODES,
    PatternEnum,
)
from apps.log_clustering.exceptions import (
    BkdataFlowException,
    BkdataStorageNotExistException,
    CollectorStorageNotExistException,
    QueryFieldsException,
)
from apps.log_clustering.handlers.aiops.base import BaseAiopsHandler
from apps.log_clustering.handlers.data_access.data_access import DataAccessHandler
from apps.log_clustering.handlers.dataflow.constants import (
    DEFAULT_CLUSTERING_FIELD,
    DEFAULT_FLINK_BATCH_SIZE,
    DEFAULT_FLINK_CPU,
    DEFAULT_FLINK_MEMORY,
    DEFAULT_FLINK_REPLICAS,
    DEFAULT_FLINK_WORKER_NUMS,
    DEFAULT_MODEL_INPUT_FIELDS,
    DEFAULT_MODEL_OUTPUT_FIELDS,
    DEFAULT_SPARK_EXECUTOR_CORES,
    DEFAULT_SPARK_EXECUTOR_INSTANCES,
    DEFAULT_SPARK_LOCALITY_WAIT,
    DEFAULT_SPARK_PSEUDO_SHUFFLE,
    DIST_CLUSTERING_FIELDS,
    DIST_FIELDS,
    DIVERSION_NODE_NAME,
    NOT_CLUSTERING_FILTER_RULE,
    NOT_CONTAIN_SQL_FIELD_LIST,
    OPERATOR_AND,
    SPLIT_TYPE,
    STREAM_SOURCE_NODE_TYPE,
    TSPIDER_STORAGE_INDEX_FIELDS,
    TSPIDER_STORAGE_NODE_TYPE,
    ActionEnum,
    ActionHandler,
    FlowMode,
    NodeType,
    OnlineTaskTrainingArgs,
    OperatorOnlineTaskEnum,
    RealTimeFlowNode,
    RealTimePredictFlowNode,
)
from apps.log_clustering.handlers.dataflow.data_cls import (
    AddFlowNodesCls,
    AfterTreatDataFlowCls,
    CreateFlowCls,
    CreateOnlineTaskCls,
    ExportFlowCls,
    HDFSStorageCls,
    LogCountAggregationFlowCls,
    MergeNodeCls,
    ModelCls,
    ModelClusterPredictNodeCls,
    ModifyFlowCls,
    OperatorFlowCls,
    PredictDataFlowCls,
    PreTreatDataFlowCls,
    RealTimeCls,
    RedisStorageCls,
    RequireNodeCls,
    SplitCls,
    StreamSourceCls,
    TspiderStorageCls,
    UpdateModelInstanceCls,
    UpdateOnlineTaskCls,
)
from apps.log_clustering.models import ClusteringConfig
from apps.log_databus.models import CollectorConfig
from apps.log_search.models import LogIndexSet
from apps.utils.log import logger


class DataFlowHandler(BaseAiopsHandler):
    def export(self, flow_id: int):
        """
        导出flow
        @param flow_id flow id
        """
        export_request = ExportFlowCls(flow_id=flow_id)
        request_dict = self._set_username(export_request)
        return BkDataDataFlowApi.export_flow(request_dict)

    @retry(stop_max_attempt_number=3, wait_random_min=3 * 60 * 1000, wait_random_max=10 * 60 * 1000)
    def operator_flow(
        self, flow_id: int, consuming_mode: str = "continue", cluster_group: str = "default", action=ActionEnum.START
    ):
        """
        启动flow
        @param flow_id flow id
        @param cluster_group 计算集群组
        @param consuming_mode 数据处理模式
        @param action 操作flow
        """
        cluster_group = self.conf.get("aiops_default_cluster_group", cluster_group)
        start_request = OperatorFlowCls(flow_id=flow_id, consuming_mode=consuming_mode, cluster_group=cluster_group)
        request_dict = self._set_username(start_request)
        return ActionHandler.get_action_handler(action_num=action)(request_dict)

    @classmethod
    def get_clustering_training_params(cls, clustering_config):
        return {
            "min_members": clustering_config.min_members,
            "st_list": OnlineTaskTrainingArgs.ST_LIST,
            "predefined_variables": clustering_config.predefined_varibles,
            "delimeter": clustering_config.delimeter,
            "max_log_length": clustering_config.max_log_length,
            "is_case_sensitive": clustering_config.is_case_sensitive,
            "depth": clustering_config.depth,
            "max_child": clustering_config.max_child,
            "use_offline_model": OnlineTaskTrainingArgs.USE_OFFLINE_MODEL,
            "max_dist_list": clustering_config.max_dist_list,
        }

    @classmethod
    def get_fields_dict(cls, clustering_config):
        """
        get_fields_dict
        @param clustering_config:
        @return:
        """
        if clustering_config.collector_config_id:
            all_etl_fields = CollectorConfig.objects.get(
                collector_config_id=clustering_config.collector_config_id
            ).get_all_etl_fields()
            return {field["field_name"]: field["alias_name"] or field["field_name"] for field in all_etl_fields}
        log_index_set_all_fields = LogIndexSet.objects.get(index_set_id=clustering_config.index_set_id).get_fields()
        return {field["field_name"]: field["field_name"] for field in log_index_set_all_fields["fields"]}

    def check_and_start_clean_task(self, result_table_id):
        """
        检查并启动清洗任务
        """
        result_table = BkDataMetaApi.result_tables.retrieve(self._set_username({"result_table_id": result_table_id}))
        if result_table["processing_type"] == "clean":
            logger.info(f"check_and_start_clean_task: result_table_id -> {result_table_id}")
            result = BkDataDatabusApi.post_tasks(
                self._set_username({"result_table_id": result_table_id, "storages": ["kafka"]})
            )
            logger.info(f"check_and_start_clean_task: result_table_id -> {result_table_id}, result -> {result}")

    def create_pre_treat_flow(self, index_set_id: int):
        """
        创建pre-treat flow
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)

        self.check_and_start_clean_task(clustering_config.bkdata_etl_result_table_id)

        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        filter_rule, not_clustering_rule = self._init_filter_rule(
            clustering_config.filter_rules, all_fields_dict, clustering_config.clustering_fields
        )
        time_format = arrow.now().format("YYYYMMDDHHmmssSSS")
        bk_biz_id = self.conf.get("bk_biz_id") if clustering_config.collector_config_id else clustering_config.bk_biz_id
        pre_treat_flow_dict = asdict(
            self._init_pre_treat_flow(
                result_table_id=clustering_config.bkdata_etl_result_table_id,
                filter_rule=filter_rule,
                not_clustering_rule=not_clustering_rule,
                clustering_fields=all_fields_dict.get(clustering_config.clustering_fields),
                time_format=time_format,
                bk_biz_id=bk_biz_id,
            )
        )
        pre_treat_flow = self._render_template(
            flow_mode=FlowMode.PRE_TREAT_FLOW.value, render_obj={"pre_treat": pre_treat_flow_dict}
        )
        flow = json.loads(pre_treat_flow)
        create_pre_treat_flow_request = CreateFlowCls(
            nodes=flow,
            flow_name="{}_{}_pre_treat_flow_{}".format(
                settings.ENVIRONMENT, clustering_config.index_set_id, time_format
            ),
            project_id=self.conf.get("project_id"),
        )
        request_dict = self._set_username(create_pre_treat_flow_request)
        result = BkDataDataFlowApi.create_flow(request_dict)
        clustering_config.pre_treat_flow = pre_treat_flow_dict
        clustering_config.pre_treat_flow_id = result["flow_id"]
        clustering_config.save()
        return result

    @classmethod
    def _init_filter_rule(cls, filter_rules, all_fields_dict, clustering_field):
        default_filter_rule = cls._init_default_filter_rule(all_fields_dict.get(clustering_field))

        rules = []
        is_not_null_rules = ""
        fields_name_list = list({all_fields_dict.get(filter_rule.get('fields_name')) for filter_rule in filter_rules})
        if fields_name_list:
            if all_fields_dict.get(clustering_field) and all_fields_dict.get(clustering_field) in fields_name_list:
                fields_name_list.remove(all_fields_dict.get(clustering_field))
            is_not_null_rules = OPERATOR_AND.join([f" `{field}` is not null " for field in fields_name_list])

        for index, filter_rule in enumerate(filter_rules):
            if not all_fields_dict.get(filter_rule.get("fields_name")):
                continue
            if index > 0:
                # 如果不是第一个条件，则把运算符加进去
                rules.append(filter_rule.get("logic_operator"))
            rules.extend(
                [
                    f"`{all_fields_dict.get(filter_rule.get('fields_name'))}`",
                    cls.change_op(filter_rule.get("op")),
                    "'{}'".format(filter_rule.get("value")),
                ]
            )

        if rules and is_not_null_rules != "":
            rules_str = " ".join([OPERATOR_AND, "(", is_not_null_rules, ")", OPERATOR_AND, "(", *rules, ")"])
        elif rules and is_not_null_rules == "":
            rules_str = " ".join([OPERATOR_AND, "(", *rules, ")"])
        else:
            rules_str = ""

        filter_rule_list = ["where", default_filter_rule, rules_str]
        not_clustering_rule_list = ["where", "NOT", "(", default_filter_rule, rules_str, ")"]
        return " ".join(filter_rule_list), " ".join(not_clustering_rule_list)

    @classmethod
    def change_op(cls, op):
        if op == "!=":
            return "<>"
        return op

    @classmethod
    def _init_default_filter_rule(cls, clustering_field):
        if not clustering_field:
            return ""
        return "`{}` is not null and length(`{}`) > 1".format(clustering_field, clustering_field)

    def _init_pre_treat_flow(
        self,
        result_table_id: str,
        filter_rule: str,
        not_clustering_rule: str,
        time_format: str,
        bk_biz_id: int,
        clustering_fields="log",
    ):
        """
        初始化预处理flow
        """
        all_fields = DataAccessHandler.get_fields(result_table_id=result_table_id)
        is_dimension_fields = [
            field["field_name"] for field in all_fields if field["field_name"] not in NOT_CONTAIN_SQL_FIELD_LIST
        ]
        dst_transform_fields, transform_fields = self._generate_fields(  # pylint: disable=unused-variable
            is_dimension_fields, clustering_field=clustering_fields
        )
        pre_treat_flow = PreTreatDataFlowCls(
            stream_source=StreamSourceCls(result_table_id=result_table_id),
            sample_set=RealTimeCls(
                fields=", ".join(transform_fields),
                table_name="pre_treat_sample_set_{}".format(time_format),
                result_table_id="{}_pre_treat_sample_set_{}".format(bk_biz_id, time_format),
                filter_rule=filter_rule,
            ),
            sample_set_hdfs=HDFSStorageCls(
                table_name="pre_treat_sample_set_{}".format(time_format), expires=self.conf.get("hdfs_expires")
            ),
            not_clustering=RealTimeCls(
                fields=", ".join([f"`{field}`" for field in is_dimension_fields]),
                table_name="pre_treat_not_clustering_{}".format(time_format),
                result_table_id="{}_pre_treat_not_clustering_{}".format(bk_biz_id, time_format),
                filter_rule=not_clustering_rule if not_clustering_rule else NOT_CLUSTERING_FILTER_RULE,
            ),
            not_clustering_hdfs=HDFSStorageCls(
                table_name="pre_treat_not_clustering_{}".format(time_format), expires=self.conf.get("hdfs_expires")
            ),
            bk_biz_id=bk_biz_id,
            cluster=self.get_model_available_storage_cluster(),
        )
        return pre_treat_flow

    @classmethod
    def _generate_fields(cls, is_dimension_fields: list, clustering_field: str):
        if clustering_field == DEFAULT_CLUSTERING_FIELD:
            return copy.copy(is_dimension_fields), copy.copy(is_dimension_fields)
        # 转换节点之后的fields数组
        dst_transform_fields = []
        # 转换节点的fields数组
        transform_fields = []
        for field in is_dimension_fields:
            if field == clustering_field:
                dst_transform_fields.append(f"`{DEFAULT_CLUSTERING_FIELD}`")
                transform_fields.append("`{}` as `{}`".format(field, DEFAULT_CLUSTERING_FIELD))
                continue
            if field == DEFAULT_CLUSTERING_FIELD:
                dst_transform_fields.append(f"`{clustering_field}`")
                transform_fields.append("`{}` as `{}`".format(field, clustering_field))
                continue
            dst_transform_fields.append(f"`{field}`")
            transform_fields.append(f"`{field}`")
        return dst_transform_fields, transform_fields

    @classmethod
    def _render_template(cls, flow_mode: str, render_obj):
        flow_path = FlowMode.get_choice_label(flow_mode)
        file_path, file_name = os.path.split(flow_path)
        file_loader = FileSystemLoader(file_path)
        env = Environment(loader=file_loader)
        template = env.get_template(file_name)
        return template.render(**render_obj)

    def create_after_treat_flow(self, index_set_id):
        """
        create_after_treat_flow
        @param index_set_id:
        @return:
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        source_rt_name = (
            clustering_config.collector_config_name_en
            if clustering_config.collector_config_name_en
            else clustering_config.source_rt_name
        )
        time_format = arrow.now().format("YYYYMMDDHHmmssSSS")
        bk_biz_id = self.conf.get("bk_biz_id") if clustering_config.collector_config_id else clustering_config.bk_biz_id

        after_treat_flow_dict = asdict(
            self._init_after_treat_flow(
                clustering_fields=all_fields_dict.get(clustering_config.clustering_fields),
                sample_set_result_table_id=clustering_config.pre_treat_flow["sample_set"]["result_table_id"],
                non_clustering_result_table_id=clustering_config.pre_treat_flow["not_clustering"]["result_table_id"],
                model_id=clustering_config.model_id,
                model_release_id=self.get_latest_released_id(clustering_config.model_id),
                src_rt_name=source_rt_name,
                target_bk_biz_id=clustering_config.bk_biz_id,
                clustering_config=clustering_config,
                time_format=time_format,
                bk_biz_id=bk_biz_id,
            )
        )
        after_treat_flow = self._render_template(
            flow_mode=FlowMode.AFTER_TREAT_FLOW.value
            if clustering_config.collector_config_id
            else FlowMode.AFTER_TREAT_FLOW_BKDATA.value,
            render_obj={"after_treat": after_treat_flow_dict},
        )
        flow = json.loads(after_treat_flow)
        new_cls_pattern_rt = after_treat_flow_dict["diversion"]["result_table_id"]
        # 这里是为了越过分流节点
        if clustering_config.bk_biz_id == self.conf.get("bk_biz_id") or not clustering_config.collector_config_id:
            flow, new_cls_pattern_rt = self.deal_diversion_node(flow=flow, after_treat_flow_dict=after_treat_flow_dict)
        create_after_treat_flow_request = CreateFlowCls(
            nodes=flow,
            flow_name="{}_{}_after_treat_flow_{}".format(
                settings.ENVIRONMENT, clustering_config.index_set_id, time_format
            ),
            project_id=self.conf.get("project_id"),
        )
        request_dict = self._set_username(create_after_treat_flow_request)
        result = BkDataDataFlowApi.create_flow(request_dict)
        clustering_config.after_treat_flow = after_treat_flow_dict
        clustering_config.after_treat_flow_id = result["flow_id"]
        clustering_config.new_cls_pattern_rt = new_cls_pattern_rt
        clustering_config.save()
        self.add_kv_source_node(
            clustering_config.after_treat_flow_id,
            clustering_config.after_treat_flow["join_signature_tmp"]["result_table_id"],
            bk_biz_id=bk_biz_id,
        )
        if clustering_config.bk_biz_id != self.conf.get("bk_biz_id") and clustering_config.collector_config_id:
            stream_source_node = self.add_stream_source(
                flow_id=clustering_config.after_treat_flow_id,
                stream_source_table_id=clustering_config.after_treat_flow["diversion"]["result_table_id"],
                target_bk_biz_id=clustering_config.bk_biz_id,
            )
            self.add_tspider_storage(
                flow_id=clustering_config.after_treat_flow_id,
                tspider_storage_table_id=clustering_config.after_treat_flow["diversion"]["result_table_id"],
                target_bk_biz_id=clustering_config.bk_biz_id,
                expires=clustering_config.after_treat_flow["diversion_tspider"]["expires"],
                cluster=clustering_config.after_treat_flow["diversion_tspider"]["cluster"],
                source_node_id=stream_source_node["node_id"],
            )
        modify_flow_dict = asdict(
            self.modify_flow(
                after_treat_flow_id=clustering_config.after_treat_flow_id,
                group_by_result_table_id=clustering_config.after_treat_flow["group_by"]["result_table_id"],
                redis_result_table_id=clustering_config.after_treat_flow["join_signature_tmp"]["result_table_id"],
                modify_node_result_table_id=clustering_config.after_treat_flow["join_signature"]["result_table_id"],
                modify_node_result_table_name=clustering_config.after_treat_flow["join_signature"]["table_name"],
                bk_biz_id=bk_biz_id,
            )
        )
        modify_flow = self._render_template(
            flow_mode=FlowMode.MODIFY_FLOW.value, render_obj={"modify_flow": modify_flow_dict}
        )
        modify_flow_json = json.loads(modify_flow)
        request_dict = self._set_username(modify_flow_json)
        clustering_config.modify_flow = modify_flow_dict
        clustering_config.save()
        flow_res = BkDataDataFlowApi.put_flow_nodes(request_dict)
        data_processing_id_config = self.get_serving_data_processing_id_config(
            clustering_config.after_treat_flow["model"]["result_table_id"]
        )
        self.update_model_instance(model_instance_id=data_processing_id_config["id"])
        return flow_res

    def deal_diversion_node(self, flow, after_treat_flow_dict):
        """
        为了处理分流节点不能分流到同业务id
        @param flow:
        @param after_treat_flow_dict:
        @return:
        """
        storage_type = self.conf.get("tspider_storage_type", TSPIDER_STORAGE_NODE_TYPE)

        for flow_obj in flow:
            if flow_obj["node_type"] == SPLIT_TYPE:
                flow.remove(flow_obj)
                flow.append(
                    {
                        "name": _("新类判断({})").format(storage_type),
                        "result_table_id": after_treat_flow_dict["judge_new_class"]["result_table_id"],
                        "bk_biz_id": after_treat_flow_dict["target_bk_biz_id"],
                        "indexed_fields": TSPIDER_STORAGE_INDEX_FIELDS,
                        "cluster": after_treat_flow_dict["diversion_tspider"]["cluster"],
                        "expires": after_treat_flow_dict["diversion_tspider"]["expires"],
                        "has_unique_key": False,
                        "storage_keys": [],
                        "id": 283090,
                        "from_nodes": [
                            {
                                "id": 268099,
                                "from_result_table_ids": [after_treat_flow_dict["judge_new_class"]["result_table_id"]],
                            }
                        ],
                        "node_type": storage_type,
                        "frontend_info": {"x": 2231, "y": 73},
                    }
                )
        return flow, after_treat_flow_dict["judge_new_class"]["result_table_id"]

    def _init_after_treat_flow(
        self,
        sample_set_result_table_id: str,
        non_clustering_result_table_id: str,
        model_release_id: int,
        model_id: str,
        target_bk_biz_id: int,
        src_rt_name: str,
        clustering_config,
        time_format: str,
        bk_biz_id: int,
        clustering_fields: str = "log",
    ):
        # 这里是为了在新类中去除第一次启动24H内产生的大量异常新类
        new_cls_timestamp = int(arrow.now().shift(hours=DEFAULT_NEW_CLS_HOURS).float_timestamp * 1000)
        all_fields = DataAccessHandler.get_fields(result_table_id=sample_set_result_table_id)
        is_dimension_fields = [
            field["field_name"] for field in all_fields if field["field_name"] not in NOT_CONTAIN_SQL_FIELD_LIST
        ]
        _, transform_fields = self._generate_fields(is_dimension_fields, clustering_field=clustering_fields)
        change_clustering_fields = copy.copy(transform_fields)
        transform_fields.extend(DIST_FIELDS)
        change_clustering_fields = [field.split(" as ")[-1] for field in change_clustering_fields]
        change_clustering_fields.extend(DIST_CLUSTERING_FIELDS)
        merge_table_table_id = "{}_bklog_{}_{}".format(bk_biz_id, settings.ENVIRONMENT, src_rt_name)
        merge_table_table_name = "bklog_{}_{}".format(settings.ENVIRONMENT, src_rt_name)
        after_treat_flow = AfterTreatDataFlowCls(
            sample_set_stream_source=StreamSourceCls(result_table_id=sample_set_result_table_id),
            non_clustering_stream_source=StreamSourceCls(result_table_id=non_clustering_result_table_id),
            model=ModelCls(
                table_name="after_treat_model_{}".format(time_format),
                model_release_id=model_release_id,
                model_id=model_id,
                result_table_id="{}_after_treat_model_{}".format(bk_biz_id, time_format),
                input_fields=json.dumps(self.get_model_input_fields(all_fields)),
                output_fields=json.dumps(self.get_model_output_fields(all_fields)),
            ),
            change_field=RealTimeCls(
                fields=", ".join(transform_fields),
                table_name="after_treat_change_field_{}".format(time_format),
                result_table_id="{}_after_treat_change_field_{}".format(bk_biz_id, time_format),
                filter_rule="",
            ),
            change_clustering_field=RealTimeCls(
                fields=", ".join(change_clustering_fields),
                table_name="change_clustering_field_{}".format(time_format),
                result_table_id="{}_change_clustering_field_{}".format(bk_biz_id, time_format),
                filter_rule="",
            ),
            merge_table=MergeNodeCls(
                table_name=merge_table_table_name,
                result_table_id=merge_table_table_id,
            ),
            format_signature=RealTimeCls(
                fields="",
                table_name="after_treat_format_signature_{}".format(time_format),
                result_table_id="{}_after_treat_format_signature_{}".format(bk_biz_id, time_format),
                filter_rule="",
            ),
            join_signature_tmp=RealTimeCls(
                fields="",
                table_name="after_treat_join_signature_tmp_{}".format(time_format),
                result_table_id="{}_after_treat_join_signature_tmp_{}".format(bk_biz_id, time_format),
                filter_rule="",
            ),
            judge_new_class=RealTimeCls(
                fields="",
                table_name="after_treat_judge_new_class_{}".format(time_format),
                result_table_id="{}_after_treat_judge_new_class_{}".format(bk_biz_id, time_format),
                filter_rule="AND event_time > {}".format(new_cls_timestamp),
            ),
            join_signature=RealTimeCls(
                fields="",
                table_name="after_treat_join_signature_{}".format(time_format),
                result_table_id="{}_after_treat_join_signature_{}".format(bk_biz_id, time_format),
                filter_rule="",
            ),
            group_by=RealTimeCls(
                fields="",
                table_name="after_treat_group_by_{}".format(time_format),
                result_table_id="{}_after_treat_group_by_{}".format(bk_biz_id, time_format),
                filter_rule="",
            ),
            diversion=SplitCls(
                table_name="after_treat_diversion_{}".format(time_format),
                result_table_id="{}_after_treat_diversion_{}".format(target_bk_biz_id, time_format),
            ),
            diversion_tspider=TspiderStorageCls(
                cluster=self.conf.get("tspider_cluster"), expires=self.conf.get("tspider_cluster_expire")
            ),
            redis=RedisStorageCls(cluster=self.conf.get("redis_cluster")),
            queue_cluster=self.conf.get("queue_cluster"),
            bk_biz_id=bk_biz_id,
            target_bk_biz_id=target_bk_biz_id,
            is_flink_env=self.conf.get("is_flink_env", False),
        )
        if not clustering_config.collector_config_id:
            es_storage = self.get_es_storage_fields(clustering_config.bkdata_etl_result_table_id)
            if not es_storage:
                raise BkdataStorageNotExistException(
                    BkdataStorageNotExistException.MESSAGE.formate(index_set_id=clustering_config.index_set_id)
                )

            after_treat_flow.es_cluster = clustering_config.es_storage
            after_treat_flow.es.expires = es_storage["expires"]
            after_treat_flow.es.has_replica = json.dumps(es_storage.get("has_replica", False))
            after_treat_flow.es.json_fields = json.dumps(es_storage.get("json_fields", []))
            after_treat_flow.es.analyzed_fields = json.dumps(es_storage.get("analyzed_fields", []))
            doc_values_fields = es_storage.get("doc_values_fields", [])
            doc_values_fields.extend(
                [f"{AGGS_FIELD_PREFIX}_{pattern_level}" for pattern_level in PatternEnum.get_dict_choices().keys()]
            )
            after_treat_flow.es.doc_values_fields = json.dumps(doc_values_fields)
            # 这里是为了避免计算平台数据源场景源索引命名重复导致创建有问题
            after_treat_flow.merge_table.table_name = "merge_table_{}".format(time_format)
            after_treat_flow.merge_table.result_table_id = "{}_merge_table_{}".format(bk_biz_id, time_format)
        return after_treat_flow

    @classmethod
    def get_model_input_fields(cls, rt_fields):
        """
        获取模型输入字段列表
        :param rt_fields: 输入结果表字段列表
        :return:
        """
        input_fields = copy.deepcopy(DEFAULT_MODEL_INPUT_FIELDS)
        default_fields = [field["field_name"] for field in input_fields]
        for field in rt_fields:
            if field["field_name"] not in default_fields and field["field_name"] not in NOT_CONTAIN_SQL_FIELD_LIST:
                input_fields.append(
                    {
                        "data_field_name": field["field_name"],
                        "roles": ["passthrough"],
                        "field_name": field["field_name"],
                        "field_type": field["field_type"],
                        "properties": {"roles": [], "role_changeable": True},
                        "field_alias": field["field_alias"],
                    }
                )
        return input_fields

    @classmethod
    def get_model_output_fields(cls, rt_fields, is_predict=False):
        """
        获取模型输出字段列表
        :param rt_fields: 输入结果表字段列表
        :return:
        """
        output_fields = copy.deepcopy(DEFAULT_MODEL_OUTPUT_FIELDS)
        default_fields = [field["field_name"] for field in output_fields]
        for field in rt_fields:
            if field["field_name"] not in default_fields and field["field_name"] not in NOT_CONTAIN_SQL_FIELD_LIST:
                output_fields.append(
                    {
                        "data_field_name": field["field_name"],
                        "roles": ["passthrough"],
                        "field_name": field["field_name"],
                        "field_type": field["field_type"],
                        "properties": {"roles": [], "role_changeable": True, "passthrough": True},
                        "field_alias": field["field_alias"],
                    }
                )
        for field in output_fields:
            # 统一加上output_mark
            field["output_mark"] = True
        if not is_predict:
            return [field for field in output_fields if field["field_name"] not in ["is_new", "pattern"]]
        return output_fields

    @classmethod
    def get_es_storage_fields(cls, result_table_id):
        """
        获取计算平台rt存储字段
        @param result_table_id:
        @return:
        """
        result = BkDataMetaApi.result_tables.storages({"result_table_id": result_table_id})
        es = result.get("es")
        if not es:
            return None
        storage_config = json.loads(es["storage_config"])
        # "expires": "3d"
        try:
            # maybe is -1
            storage_config["expires"] = int(es["expires"])
        except ValueError:
            storage_config["expires"] = int(es["expires"][:-1])

        return storage_config

    def add_kv_source_node(self, flow_id, kv_source_result_table_id, bk_biz_id):
        """
        给flow添加kv_source节点
        @param flow_id:
        @param kv_source_result_table_id:
        @param bk_biz_id:
        @return:
        """
        add_kv_source_node_request = AddFlowNodesCls(
            flow_id=flow_id,
            result_table_id=kv_source_result_table_id,
        )
        add_kv_source_node_request.config["bk_biz_id"] = bk_biz_id
        add_kv_source_node_request.config["from_result_table_ids"].append(kv_source_result_table_id)
        add_kv_source_node_request.config["result_table_id"] = kv_source_result_table_id
        request_dict = self._set_username(add_kv_source_node_request)
        return BkDataDataFlowApi.add_flow_nodes(request_dict)

    def add_stream_source(self, flow_id, stream_source_table_id, target_bk_biz_id):
        """
        add_stream_source
        @param flow_id:
        @param stream_source_table_id:
        @param target_bk_biz_id:
        @return:
        """
        add_stream_source_request = AddFlowNodesCls(
            flow_id=flow_id,
            result_table_id=stream_source_table_id,
        )
        add_stream_source_request.config["bk_biz_id"] = target_bk_biz_id
        add_stream_source_request.config["from_result_table_ids"].append(stream_source_table_id)
        add_stream_source_request.config["result_table_id"] = stream_source_table_id
        add_stream_source_request.config["name"] = DIVERSION_NODE_NAME
        add_stream_source_request.node_type = STREAM_SOURCE_NODE_TYPE
        request_dict = self._set_username(add_stream_source_request)
        return BkDataDataFlowApi.add_flow_nodes(request_dict)

    def add_tspider_storage(
        self, flow_id, tspider_storage_table_id, target_bk_biz_id, expires, cluster, source_node_id
    ):
        """
        add_tspider_storage
        @param flow_id:
        @param tspider_storage_table_id:
        @param target_bk_biz_id:
        @param expires:
        @param cluster:
        @param source_node_id:
        @return:
        """
        storage_type = self.conf.get("tspider_storage_type", TSPIDER_STORAGE_NODE_TYPE)

        add_tspider_storage_request = AddFlowNodesCls(
            flow_id=flow_id,
            result_table_id=tspider_storage_table_id,
        )
        add_tspider_storage_request.config["bk_biz_id"] = target_bk_biz_id
        add_tspider_storage_request.config["from_result_table_ids"].append(tspider_storage_table_id)
        add_tspider_storage_request.config["result_table_id"] = tspider_storage_table_id
        add_tspider_storage_request.config["name"] = _("回流数据({})").format(storage_type)
        add_tspider_storage_request.config["expires"] = expires
        add_tspider_storage_request.config["indexed_fields"] = TSPIDER_STORAGE_INDEX_FIELDS
        add_tspider_storage_request.config["cluster"] = cluster
        add_tspider_storage_request.from_links.append(
            {
                "source": {"node_id": source_node_id, "id": "ch_{}".format(source_node_id), "arrow": "left"},
                "target": {
                    # 这里为为了契合计算平台的一个demo id 实际不起作用
                    "id": "ch_1536",
                    "arrow": "Left",
                },
            }
        )
        add_tspider_storage_request.node_type = storage_type
        request_dict = self._set_username(add_tspider_storage_request)
        return BkDataDataFlowApi.add_flow_nodes(request_dict)

    def modify_flow(
        self,
        after_treat_flow_id: int,
        group_by_result_table_id: str,
        redis_result_table_id: str,
        modify_node_result_table_id: str,
        modify_node_result_table_name: str,
        bk_biz_id: int,
    ):
        """
        modify_flow
        @param after_treat_flow_id:
        @param group_by_result_table_id:
        @param redis_result_table_id:
        @param modify_node_result_table_id:
        @param modify_node_result_table_name:
        @param bk_biz_id:
        @return:
        """
        graph = BkDataDataFlowApi.get_flow_graph(
            params={"flow_id": after_treat_flow_id, "bk_username": self.conf.get("bk_username")}
        )
        graph_nodes_dict = {
            (node["result_table_ids"][0], node["node_type"]): node["node_id"] for node in graph["nodes"]
        }
        modify_flow_cls = ModifyFlowCls(
            flow_id=after_treat_flow_id,
            node_id=graph_nodes_dict.get((modify_node_result_table_id, NodeType.REALTIME)),
            id="ch_{}".format(graph_nodes_dict.get((modify_node_result_table_id, NodeType.REALTIME))),
            bk_biz_id=bk_biz_id,
            table_name=modify_node_result_table_name,
            group_by_node=RequireNodeCls(
                node_id=graph_nodes_dict.get((group_by_result_table_id, NodeType.REALTIME)),
                result_table_id=group_by_result_table_id,
                id="ch_{}".format(graph_nodes_dict.get((group_by_result_table_id, NodeType.REALTIME))),
            ),
            redis_node=RequireNodeCls(
                node_id=graph_nodes_dict.get((redis_result_table_id, NodeType.REDIS_KV_SOURCE)),
                result_table_id=redis_result_table_id,
                id="ch_{}".format(graph_nodes_dict.get((redis_result_table_id, NodeType.REDIS_KV_SOURCE))),
            ),
        )
        return modify_flow_cls

    def get_latest_deploy_data(self, flow_id):
        """
        get_latest_deploy_data
        @param flow_id:
        @return:
        """
        return BkDataDataFlowApi.get_latest_deploy_data(
            params={"flow_id": flow_id, "bk_username": self.conf.get("bk_username")},
            data_api_retry_cls=DataApiRetryClass.create_retry_obj(
                fail_check_functions=[check_result_is_true], stop_max_attempt_number=MAX_FAILED_REQUEST_RETRY
            ),
        )

    def get_serving_data_processing_id_config(self, result_table_id):
        """
        get_serving_data_processing_id_config
        @param result_table_id:
        @return:
        """
        return BkDataAIOPSApi.serving_data_processing_id_config(
            params={"data_processing_id": result_table_id, "bk_username": self.conf.get("bk_username")}
        )

    def get_model_available_storage_cluster(self):
        """
        get_model_available_storage_cluster
        @return:
        """
        available_storage_cluster = self.conf.get("hdfs_cluster")
        result = BkDataAIOPSApi.aiops_get_model_storage_cluster(params={"project_id": self.conf.get("project_id")})
        if not result:
            return available_storage_cluster

        for cluster_group in result:
            clusters = cluster_group.get("clusters", [])
            if clusters:
                available_storage_cluster = clusters[0]["cluster_name"]
                break
        return available_storage_cluster

    def update_model_instance(self, model_instance_id):
        """
        update_model_instance
        @param model_instance_id:
        @return:
        """
        is_flink_env = self.conf.get("is_flink_env", False)

        if is_flink_env:
            execute_config = {
                "batch_size": self.conf.get("flink.batch_size", DEFAULT_FLINK_BATCH_SIZE),
                "resource_requirement": {
                    "core": self.conf.get("flink.cpu", DEFAULT_FLINK_CPU),
                    "memory": self.conf.get("flink.memory", DEFAULT_FLINK_MEMORY),
                    "worker_nums": self.conf.get("flink.worker_nums", DEFAULT_FLINK_WORKER_NUMS),
                    "replicas": self.conf.get("flink.replicas", DEFAULT_FLINK_REPLICAS),
                },
            }
        else:
            execute_config = {
                "spark.executor.instances": self.conf.get("spark.executor.instances", DEFAULT_SPARK_EXECUTOR_INSTANCES),
                "spark.executor.cores": self.conf.get("spark.executor.cores", DEFAULT_SPARK_EXECUTOR_CORES),
                "spark.locality.wait": self.conf.get("spark.locality.wait", DEFAULT_SPARK_LOCALITY_WAIT),
                "pseudo_shuffle": self.conf.get("pseudo_shuffle", DEFAULT_SPARK_PSEUDO_SHUFFLE),
            }

        execute_config.update({"dropna_enabled": False})

        update_model_instance_request = UpdateModelInstanceCls(
            filter_id=model_instance_id,
            execute_config=execute_config,
        )
        request_dict = self._set_username(update_model_instance_request)
        return BkDataAIOPSApi.update_execute_config(request_dict)

    def update_filter_rules(self, index_set_id):
        """
        update_filter_rules
        @param index_set_id:
        @return:
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        filter_rule, not_clustering_rule = self._init_filter_rule(
            clustering_config.filter_rules, all_fields_dict, clustering_config.clustering_fields
        )

        flow_id = clustering_config.pre_treat_flow_id
        flow_graph = self.get_flow_graph(flow_id=flow_id)

        nodes = flow_graph["nodes"]
        target_nodes = self.get_flow_node_config(
            nodes=nodes,
            filter_table_names=[RealTimeFlowNode.PRE_TREAT_SAMPLE_SET, RealTimeFlowNode.PRE_TREAT_NOT_CLUSTERING],
        )

        self.deal_update_filter_flow_node(
            target_nodes=target_nodes,
            filter_rule=filter_rule,
            not_clustering_rule=not_clustering_rule if not_clustering_rule else NOT_CLUSTERING_FILTER_RULE,
            flow_id=flow_id,
        )
        self.operator_flow(flow_id=flow_id, action=ActionEnum.RESTART)

    def update_predict_flow_filter_rules(self, index_set_id):
        """
        update_predict_flow_filter_rules
        @param index_set_id:
        @return:
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        filter_rule, not_clustering_rule = self._init_filter_rule(
            clustering_config.filter_rules, all_fields_dict, clustering_config.clustering_fields
        )

        flow_id = clustering_config.predict_flow_id
        flow_graph = self.get_flow_graph(flow_id=flow_id)

        nodes = flow_graph["nodes"]
        target_nodes = self.get_predict_flow_node_config(nodes=nodes)
        self.deal_update_filter_predict_flow_node(
            target_nodes=target_nodes,
            filter_rule=filter_rule,
            not_clustering_rule=not_clustering_rule if not_clustering_rule else NOT_CLUSTERING_FILTER_RULE,
            flow_id=flow_id,
        )
        self.operator_flow(flow_id=flow_id, action=ActionEnum.RESTART)

    def update_online_task(self, index_set_id: int):
        """
        更新在线训练任务
        """
        request_dict = self.get_online_task_request(index_set_id, OperatorOnlineTaskEnum.UPDATE)
        return BkDataAIOPSApi.update_online_task(request_dict)

    def update_predict_node(self, index_set_id):
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        predict_change_args = {
            "min_members": clustering_config.min_members,
            "max_dist_list": clustering_config.max_dist_list,
            # 单词不一致 注意
            "predefined_variables": clustering_config.predefined_varibles,
            "delimeter": clustering_config.delimeter,
            "max_log_length": clustering_config.max_log_length,
            "is_case_sensitive": clustering_config.is_case_sensitive,
        }

        flow_id = clustering_config.predict_flow_id  # 预测 flow_id
        flow_graph = self.get_flow_graph(flow_id=flow_id)
        nodes = flow_graph["nodes"]
        predict_node = self.get_predict_node_config(nodes=nodes)
        # 更新预测节点
        self.deal_update_predict_node(
            predict_node=predict_node, flow_id=flow_id, predict_change_args=predict_change_args
        )

    def update_predict_nodes_and_online_tasks(self, index_set_id):
        """
        更新预测节点 更新在线训练任务
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)

        # 更新模型训练节点 (预测节点)
        self.update_predict_node(index_set_id=index_set_id)

        # 更新在线训练任务
        self.update_online_task(index_set_id=index_set_id)

        # 重启 flow
        self.operator_flow(flow_id=clustering_config.predict_flow_id, action=ActionEnum.RESTART)
        logger.info(f"update predict_nodes and online_tasks success: flow_id -> {clustering_config.predict_flow_id}")

    def get_flow_graph(self, flow_id):
        """
        get_flow_graph
        @param flow_id:
        @return:
        """
        return BkDataDataFlowApi.get_flow_graph(self._set_username(request_data_cls={"flow_id": flow_id}))

    def update_flow_nodes(self, config, flow_id, node_id):
        """
        update_flow_nodes
        @param config:
        @param flow_id:
        @param node_id:
        @return:
        """
        return BkDataDataFlowApi.patch_flow_nodes(
            self._set_username(request_data_cls={"flow_id": flow_id, "node_id": node_id, **config})
        )

    @staticmethod
    def get_flow_node_config(nodes, filter_table_names: list):
        """
        get_flow_node_config
        @param nodes:
        @param filter_table_names:
        @return:
        """
        result = {}
        for node in nodes:
            table_name = node["node_config"].get("table_name")
            if not table_name:
                continue
            table_name_prefix = table_name.rsplit("_", 1)[0]
            if table_name_prefix in filter_table_names:
                result[table_name_prefix] = node
        return result

    @staticmethod
    def get_predict_flow_node_config(nodes):
        """
        get_flow_node_config
        @param nodes:
        @return:
        """
        result = {}
        for node in nodes:
            table_name = node["node_config"].get("table_name")
            if not table_name:
                continue
            # 参与聚类节点和不参与聚类节点
            # 注意: PREDICT_NOT_CLUSTERING 的值包含了 PREDICT_CLUSTERING，因此 if-else 必须优先判断 PREDICT_NOT_CLUSTERING
            if table_name.endswith(RealTimePredictFlowNode.PREDICT_NOT_CLUSTERING):
                result[RealTimePredictFlowNode.PREDICT_NOT_CLUSTERING] = node
            elif table_name.endswith(RealTimePredictFlowNode.PREDICT_CLUSTERING):
                result[RealTimePredictFlowNode.PREDICT_CLUSTERING] = node
            else:
                continue
        return result

    @staticmethod
    def get_predict_node_config(nodes):
        """
        get_flow_node_config
        @param nodes:
        @return:
        """
        for node in nodes:
            table_name = node["node_config"].get("table_name")
            if not table_name:
                continue
            # 预测节点
            if table_name.endswith(RealTimePredictFlowNode.PREDICT_NODE):
                return node

    def deal_update_filter_predict_flow_node(self, target_nodes, filter_rule, not_clustering_rule, flow_id):
        """
        deal_update_filter_flow_node
        @param target_nodes:
        @param filter_rule:
        @param not_clustering_rule:
        @param flow_id:
        @return:
        """
        filter_nodes = target_nodes.get(RealTimePredictFlowNode.PREDICT_CLUSTERING)
        if filter_nodes:
            sql = self.deal_filter_sql(filter_nodes["node_config"]["sql"].split("where")[0], filter_rule)
            self.update_flow_nodes({"sql": sql}, flow_id=flow_id, node_id=filter_nodes["node_id"])
        not_cluster_nodes = target_nodes.get(RealTimePredictFlowNode.PREDICT_NOT_CLUSTERING)
        if not_cluster_nodes:
            sql = self.deal_filter_sql(not_cluster_nodes["node_config"]["sql"].split("where")[0], not_clustering_rule)
            self.update_flow_nodes({"sql": sql}, flow_id=flow_id, node_id=not_cluster_nodes["node_id"])

    def deal_update_predict_node(self, predict_node, flow_id, predict_change_args):
        if predict_node:
            model_extra_config = predict_node["node_config"]["model_extra_config"]
            predict_args = model_extra_config.get("predict_args", {})
            for predict in predict_args:
                for arg in predict_change_args:
                    if predict["field_name"] == arg:
                        predict["default_value"] = predict_change_args[arg]
                        predict["value"] = predict_change_args[arg]
                        predict["sample_value"] = predict_change_args[arg]
            self.update_flow_nodes(
                {"model_extra_config": model_extra_config}, flow_id=flow_id, node_id=predict_node["node_id"]
            )
        else:
            logger.error("could not find filter_nodes --> [predict_flow_id]: %s", flow_id)

    def deal_update_filter_flow_node(self, target_nodes, filter_rule, not_clustering_rule, flow_id):
        """
        deal_update_filter_flow_node
        @param target_nodes:
        @param filter_rule:
        @param not_clustering_rule:
        @param flow_id:
        @return:
        """
        filter_nodes = target_nodes.get(RealTimeFlowNode.PRE_TREAT_SAMPLE_SET)
        if filter_nodes:
            sql = self.deal_filter_sql(filter_nodes["node_config"]["sql"].split("where")[0], filter_rule)
            self.update_flow_nodes({"sql": sql}, flow_id=flow_id, node_id=filter_nodes["node_id"])
        not_cluster_nodes = target_nodes.get(RealTimeFlowNode.PRE_TREAT_NOT_CLUSTERING)
        if not_cluster_nodes:
            sql = self.deal_filter_sql(not_cluster_nodes["node_config"]["sql"].split("where")[0], not_clustering_rule)
            self.update_flow_nodes({"sql": sql}, flow_id=flow_id, node_id=not_cluster_nodes["node_id"])

    @staticmethod
    def deal_filter_sql(sql, rule):
        return f"{sql} {rule}"

    def update_flow(self, index_set_id):
        """
        update_flow
        @param index_set_id:
        @return:
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        if not clustering_config.after_treat_flow_id:
            logger.info(f"update after_treat flow not found: index_set_id -> {index_set_id}")
            return
        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        filter_rule, not_clustering_rule = self._init_filter_rule(
            clustering_config.filter_rules, all_fields_dict, clustering_config.clustering_fields
        )
        logger.info(f"update pre_treat flow beginning: flow_id -> {clustering_config.pre_treat_flow_id}")
        self.update_pre_treat_flow(
            flow_id=clustering_config.pre_treat_flow_id,
            result_table_id=clustering_config.bkdata_etl_result_table_id,
            filter_rule=filter_rule,
            not_clustering_rule=not_clustering_rule,
            clustering_fields=all_fields_dict.get(clustering_config.clustering_fields),
            clustering_config=clustering_config,
        )
        logger.info(f"update pre_treat flow success: flow_id -> {clustering_config.pre_treat_flow_id}")
        logger.info(f"update after_treat flow beginning: flow_id -> {clustering_config.after_treat_flow_id}")
        self.update_after_treat_flow(
            flow_id=clustering_config.after_treat_flow_id,
            all_fields_dict=all_fields_dict,
            clustering_config=clustering_config,
        )
        logger.info(f"update after_treat flow success: flow_id -> {clustering_config.after_treat_flow_id}")

    def update_pre_treat_flow(
        self,
        flow_id,
        result_table_id: str,
        filter_rule: str,
        not_clustering_rule: str,
        clustering_config,
        clustering_fields="log",
    ):
        """
        update_pre_treat_flow
        @param flow_id:
        @param result_table_id:
        @param filter_rule:
        @param not_clustering_rule:
        @param clustering_config:
        @param clustering_fields:
        @return:
        """
        flow_graph = self.get_flow_graph(flow_id=flow_id)
        nodes = flow_graph["nodes"]
        time_format = self.get_time_format(
            nodes=nodes, table_name_prefix=RealTimeFlowNode.PRE_TREAT_SAMPLE_SET, flow_id=flow_id
        )
        bk_biz_id = self.conf.get("bk_biz_id") if clustering_config.collector_config_id else clustering_config.bk_biz_id
        pre_treat_flow_dict = asdict(
            self._init_pre_treat_flow(
                result_table_id,
                filter_rule,
                not_clustering_rule,
                time_format,
                clustering_fields=clustering_fields,
                bk_biz_id=bk_biz_id,
            )
        )
        pre_treat_flow = self._render_template(
            flow_mode=FlowMode.PRE_TREAT_FLOW.value, render_obj={"pre_treat": pre_treat_flow_dict}
        )
        flow = json.loads(pre_treat_flow)
        self.deal_pre_treat_flow(nodes=nodes, flow=flow)
        self.operator_flow(flow_id=flow_id, action=ActionEnum.RESTART)

    def deal_predict_flow(self, nodes, flow):
        """
        deal_pre_treat_flow
        @param nodes:
        @param flow:
        @return:
        """
        target_real_time_node_dict, source_real_time_node_dict = self.get_real_time_nodes(flow=flow, nodes=nodes)
        for table_name, node in source_real_time_node_dict.items():
            target_node = target_real_time_node_dict.get(table_name)
            if not target_node:
                logger.error("could not find target_node --> [table_name]: %s", table_name)
                continue
            self.deal_real_time_node(flow_id=node["flow_id"], node_id=node["node_id"], sql=target_node["sql"])
        return

    def deal_pre_treat_flow(self, nodes, flow):
        """
        deal_pre_treat_flow
        @param nodes:
        @param flow:
        @return:
        """
        target_real_time_node_dict, source_real_time_node_dict = self.get_real_time_nodes(flow=flow, nodes=nodes)
        for table_name, node in source_real_time_node_dict.items():
            target_node = target_real_time_node_dict.get(table_name)
            if not target_node:
                logger.error("could not find target_node --> [table_name]: %s", table_name)
                continue
            self.deal_real_time_node(flow_id=node["flow_id"], node_id=node["node_id"], sql=target_node["sql"])
        return

    @classmethod
    def get_real_time_nodes(cls, flow, nodes):
        """
        get_real_time_nodes
        @param flow:
        @param nodes:
        @return:
        """
        target_real_time_node_dict = {
            node["table_name"]: node for node in flow if node["node_type"] == NodeType.REALTIME
        }
        source_real_time_node_dict = {
            node["node_config"]["table_name"]: node for node in nodes if node["node_type"] == NodeType.REALTIME
        }
        return target_real_time_node_dict, source_real_time_node_dict

    @classmethod
    def get_elasticsearch_storage_nodes(cls, flow, nodes):
        """
        get_elasticsearch_storage_nodes
        @param flow:
        @param nodes:
        @return:
        """
        target_es_storage_node_dict = {
            node["result_table_id"]: node for node in flow if node["node_type"] == NodeType.ELASTIC_STORAGE
        }
        source_es_storage_node_dict = {
            node["node_config"]["result_table_id"]: node
            for node in nodes
            if node["node_type"] == NodeType.ELASTIC_STORAGE
        }
        return target_es_storage_node_dict, source_es_storage_node_dict

    @classmethod
    def get_model_node(cls, flow, nodes):
        """
        get_model_node
        @param flow:
        @param nodes:
        @return:
        """
        target_model_node = None
        for node in flow:
            if node["node_type"] == NodeType.MODEL:
                target_model_node = node

        source_model_node = None
        for node in nodes:
            if node["node_type"] == NodeType.MODEL:
                source_model_node = node

        return target_model_node, source_model_node

    def update_after_treat_flow(self, flow_id, all_fields_dict, clustering_config):
        """
        update_after_treat_flow
        @param flow_id:
        @param all_fields_dict:
        @param clustering_config:
        @return:
        """
        flow_graph = self.get_flow_graph(flow_id=flow_id)
        nodes = flow_graph["nodes"]
        time_format = self.get_time_format(
            nodes=nodes, table_name_prefix=RealTimeFlowNode.AFTER_TREAT_CHANGE_FIELD, flow_id=flow_id
        )

        source_rt_name = (
            clustering_config.collector_config_name_en
            if clustering_config.collector_config_name_en
            else clustering_config.source_rt_name
        )
        bk_biz_id = self.conf.get("bk_biz_id") if clustering_config.collector_config_id else clustering_config.bk_biz_id
        after_treat_flow_dict = asdict(
            self._init_after_treat_flow(
                clustering_fields=all_fields_dict.get(clustering_config.clustering_fields),
                sample_set_result_table_id=clustering_config.pre_treat_flow["sample_set"]["result_table_id"],
                non_clustering_result_table_id=clustering_config.pre_treat_flow["not_clustering"]["result_table_id"],
                model_id=clustering_config.model_id,
                model_release_id=self.get_latest_released_id(clustering_config.model_id),
                src_rt_name=source_rt_name,
                target_bk_biz_id=clustering_config.bk_biz_id,
                clustering_config=clustering_config,
                time_format=time_format,
                bk_biz_id=bk_biz_id,
            )
        )
        after_treat_flow = self._render_template(
            flow_mode=FlowMode.AFTER_TREAT_FLOW.value
            if clustering_config.collector_config_id
            else FlowMode.AFTER_TREAT_FLOW_BKDATA.value,
            render_obj={"after_treat": after_treat_flow_dict},
        )
        flow = json.loads(after_treat_flow)
        self.deal_after_treat_flow(nodes=nodes, flow=flow)
        self.operator_flow(flow_id=flow_id, action=ActionEnum.RESTART)

    def deal_after_treat_flow(self, nodes, flow):
        """
        模型应用节点更新
        @param nodes:
        @param flow:
        @return:
        """
        target_model_node, source_model_node = self.get_model_node(flow=flow, nodes=nodes)
        if not target_model_node:
            logger.error(f"could not find target model node, nodes: {nodes}")
            return
        self.deal_model_node(
            flow_id=source_model_node["flow_id"],
            node_id=source_model_node["node_id"],
            input_config=target_model_node["input_config"],
            output_config=target_model_node["output_config"],
        )

        target_real_time_node_dict, source_real_time_node_dict = self.get_real_time_nodes(flow=flow, nodes=nodes)
        for table_name, node in source_real_time_node_dict.items():
            if node["node_name"] in NOT_NEED_EDIT_NODES:
                continue
            target_node = target_real_time_node_dict.get(table_name)
            if not target_node:
                logger.error("could not find target_node --> [table_name]: %s", table_name)
                continue
            self.deal_real_time_node(flow_id=node["flow_id"], node_id=node["node_id"], sql=target_node["sql"])

        target_es_storage_node_dict, source_es_storage_node_dict = self.get_elasticsearch_storage_nodes(
            flow=flow, nodes=nodes
        )
        for result_table_id, node in source_es_storage_node_dict.items():
            target_node = target_es_storage_node_dict.get(result_table_id)
            if not target_node:
                logger.error("could not find target_node --> [result_table_id]: %s", result_table_id)
                continue
            self.deal_elastic_storage_node(
                flow_id=node["flow_id"],
                node_id=node["node_id"],
                analyzed_fields=target_node["analyzed_fields"],
                date_fields=target_node["date_fields"],
                doc_values_fields=target_node["doc_values_fields"],
                json_fields=target_node["json_fields"],
            )

    def deal_model_node(self, flow_id, node_id, input_config, output_config):
        return self.update_flow_nodes(
            config={"input_config": input_config, "output_config": output_config}, flow_id=flow_id, node_id=node_id
        )

    def deal_real_time_node(self, flow_id, node_id, sql):
        return self.update_flow_nodes(config={"sql": sql}, flow_id=flow_id, node_id=node_id)

    def deal_elastic_storage_node(self, flow_id, node_id, analyzed_fields, date_fields, doc_values_fields, json_fields):
        """
        deal_elastic_storage_node
        @param flow_id:
        @param node_id:
        @param analyzed_fields:
        @param date_fields:
        @param doc_values_fields:
        @param json_fields:
        @return:
        """
        return self.update_flow_nodes(
            config={
                "analyzed_fields": analyzed_fields,
                "date_fields": date_fields,
                "doc_values_fields": doc_values_fields,
                "json_fields": json_fields,
            },
            flow_id=flow_id,
            node_id=node_id,
        )

    def get_time_format(self, nodes, table_name_prefix, flow_id):
        """
        get_time_format
        @param nodes:
        @param table_name_prefix:
        @param flow_id:
        @return:
        """
        target_nodes = self.get_flow_node_config(nodes=nodes, filter_table_names=[table_name_prefix])
        if not target_nodes:
            raise BkdataFlowException(BkdataFlowException.MESSAGE.format(flow_id=flow_id))

        return target_nodes[table_name_prefix]["node_config"]["table_name"].rsplit("_", 1)[1]

    def get_online_task_request(self, index_set_id: int, operator: str):
        """在线任务请求参数"""

        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        pipeline_params = {
            # data_set_id  聚类预测结果 output_name
            "data_set_id": clustering_config.predict_flow['clustering_predict']['result_table_id'],
            "data_set_type": "result_table",
            "data_set_mode": "incremental",
            "sampling_conditions": [{"field_name": "is_new", "value": OnlineTaskTrainingArgs.IS_NEW}],
            "training_args": [
                {"field_name": "min_members", "value": clustering_config.min_members},
                {"field_name": "max_dist_list", "value": clustering_config.max_dist_list},
                {"field_name": "st_list", "value": OnlineTaskTrainingArgs.ST_LIST},
                {
                    "field_name": "predefined_variables",
                    "value": clustering_config.predefined_varibles,  # 单词错误 predefined_variables
                },
                {"field_name": "delimeter", "value": clustering_config.delimeter},
                {"field_name": "max_log_length", "value": clustering_config.max_log_length},
                {"field_name": "is_case_sensitive", "value": clustering_config.is_case_sensitive},
                {"field_name": "depth", "value": clustering_config.depth},
                {"field_name": "max_child", "value": clustering_config.max_child},
                {
                    # 是否以离线模型作为基础模型  0 不使用离线模型
                    "field_name": "use_offline_model",
                    "value": OnlineTaskTrainingArgs.USE_OFFLINE_MODEL,
                },
            ],
            "training_input": [
                {
                    # 前置环节已经转换 message 为 log
                    "field_name": "log",
                    "data_field_name": DEFAULT_CLUSTERING_FIELD,
                }
            ],
        }
        # 模型应用 id
        data_processing_id_config = self.get_serving_data_processing_id_config(
            clustering_config.predict_flow['clustering_predict']["result_table_id"]
        )
        if operator == OperatorOnlineTaskEnum.UPDATE:
            update_online_task_request = UpdateOnlineTaskCls(
                model_instance_id=data_processing_id_config["id"],
                pipeline_params=pipeline_params,
                trigger={"auto_trigger_type": "stream_event"},
                aiops_stage="serving_stream_ci",
                online_task_id=clustering_config.online_task_id,
            )
            request_dict = self._set_username(update_online_task_request)

        elif operator == OperatorOnlineTaskEnum.CREATE:
            create_online_task_request = CreateOnlineTaskCls(
                model_instance_id=data_processing_id_config["id"],
                pipeline_params=pipeline_params,
                trigger={"auto_trigger_type": "stream_event"},
                aiops_stage="serving_stream_ci",
            )
            request_dict = self._set_username(create_online_task_request)
        else:
            raise Exception(f"invalid online task operator: {operator}, only support create or update")
        return request_dict

    def create_online_task(self, index_set_id: int):
        """
        创建在线任务
        """

        request_dict = self.get_online_task_request(index_set_id, OperatorOnlineTaskEnum.CREATE)
        return BkDataAIOPSApi.create_online_task(request_dict)

    def _init_predict_flow(
        self,
        result_table_id: str,
        model_id: str,
        model_release_id: int,
        bk_biz_id: int,
        index_set_id: int,
        clustering_config,
        clustering_fields="log",
    ):
        """
        初始化 predict_flow
        回填模版中需要的字段  比如 es或者 queue
        需要根据节点来确定具体的参数
        """
        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        # 从BkDataMetaApi 获取字段信息  用于回填模版
        all_fields = DataAccessHandler.get_fields(result_table_id=result_table_id)
        exclude_message_fields = [field for field in all_fields if field["field_name"] != clustering_fields]
        # 去除不聚类的字段 转换前所有字段  比如 meeage 转换成 log
        is_dimension_fields = [
            field["field_name"] for field in all_fields if field["field_name"] not in NOT_CONTAIN_SQL_FIELD_LIST
        ]
        dst_transform_fields, transform_fields = self._generate_fields(
            is_dimension_fields, clustering_field=clustering_fields
        )
        filter_rule, not_clustering_rule = self._init_filter_rule(
            clustering_config.filter_rules, all_fields_dict, clustering_config.clustering_fields
        )
        _, format_transform_fields = self._generate_fields(
            [i.replace("`", "") for i in dst_transform_fields], clustering_field=clustering_fields
        )
        # 参与聚类的 table_name  是 result_table_id去掉第一个_前的数字
        table_name_no_id = result_table_id.split("_", 1)[1]

        predict_flow = PredictDataFlowCls(
            table_name_no_id=table_name_no_id,
            result_table_id=result_table_id,
            # 参与聚类
            clustering_stream_source=RealTimeCls(
                fields=", ".join(transform_fields),
                table_name=f"bklog_{index_set_id}_clustering",
                result_table_id=f"{bk_biz_id}_bklog_{index_set_id}_clustering",
                filter_rule=filter_rule,
            ),
            # 聚类预测
            clustering_predict=ModelClusterPredictNodeCls(
                table_name=f"bklog_{index_set_id}_clustering_output",
                result_table_id=f"{bk_biz_id}_bklog_{index_set_id}_clustering_output",
                clustering_training_params=self.get_clustering_training_params(clustering_config=clustering_config),
                model_release_id=model_release_id,
                model_id=model_id,
                input_fields=json.dumps(self.get_model_input_fields(exclude_message_fields)),
                output_fields=json.dumps(self.get_model_output_fields(exclude_message_fields, is_predict=True)),
            ),
            # 签名字段打平
            format_signature=RealTimeCls(
                fields=", ".join(format_transform_fields),
                table_name=f"bklog_{index_set_id}_clustered",
                result_table_id=f"{bk_biz_id}_bklog_{index_set_id}_clustered",
                filter_rule="",
            ),
            bk_biz_id=bk_biz_id,
            is_flink_env=self.conf.get("is_flink_env", False),
        )
        # 采集项侧，创建聚类配置时设置 es_storage
        if clustering_config.collector_config_id:
            """
            采集项侧配置的 es_storage
            {
            'es_storage': 'xxx',
            'has_replica': 'false',
            'expires': x,
            'json_fields': [],
            'analyzed_fields': [],
            'doc_values_fields': []
            }
            """
            # 采集项侧配置的 es_storage
            es_storage = self.conf.get("collector_clustering_es_storage", {})
            if not es_storage:
                raise CollectorStorageNotExistException(
                    CollectorStorageNotExistException.MESSAGE.formate(index_set_id=clustering_config.index_set_id)
                )
            # es_storage["expires"] =
            log_index_set = LogIndexSet.objects.filter(index_set_id=index_set_id).first()
            fields = log_index_set.get_fields()
            if not fields:
                raise QueryFieldsException(QueryFieldsException.MESSAGE.formate(index_set_id=index_set_id))
            es_storage["doc_values_fields"] = [
                i["field_name"] or i["field_alias"] for i in fields["fields"] if i["es_doc_values"]
            ]
            es_storage["analyzed_fields"] = [
                i["field_name"] or i["field_alias"] for i in fields["fields"] if i["is_analyzed"]
            ]
            es_storage["json_fields"] = [
                i["field_name"] or i["field_alias"] for i in fields["fields"] if i["field_type"] == "object"
            ]
            collector_config = CollectorConfig.objects.get(collector_config_id=clustering_config.collector_config_id)
            es_storage["expires"] = str(collector_config.retention)
        else:
            # es输出的配置(计算平台和采集项均输出es存储)
            es_storage = self.get_es_storage_fields(clustering_config.bkdata_etl_result_table_id)
            if not es_storage:
                raise BkdataStorageNotExistException(
                    BkdataStorageNotExistException.MESSAGE.formate(index_set_id=clustering_config.index_set_id)
                )
        predict_flow.es_cluster = clustering_config.es_storage
        predict_flow.es.expires = es_storage["expires"]
        predict_flow.es.has_replica = json.dumps(es_storage.get("has_replica", False))
        predict_flow.es.json_fields = json.dumps(es_storage.get("json_fields", []))
        predict_flow.es.analyzed_fields = json.dumps(es_storage.get("analyzed_fields", []))
        doc_values_fields = es_storage.get("doc_values_fields", [])
        doc_values_fields.extend(
            [f"{AGGS_FIELD_PREFIX}_{pattern_level}" for pattern_level in PatternEnum.get_dict_choices().keys()]
        )
        predict_flow.es.doc_values_fields = json.dumps(doc_values_fields)

        return predict_flow

    def create_predict_flow(self, index_set_id: int):
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        predict_flow_dict = asdict(
            self._init_predict_flow(
                result_table_id=clustering_config.bkdata_etl_result_table_id,
                model_id=clustering_config.model_id,
                model_release_id=self.get_latest_released_id(clustering_config.model_id),
                bk_biz_id=clustering_config.bk_biz_id,
                index_set_id=index_set_id,
                clustering_config=clustering_config,
                clustering_fields=all_fields_dict.get(clustering_config.clustering_fields),
            )
        )
        predict_flow = self._render_template(
            flow_mode=FlowMode.PREDICT_FLOW.value,
            render_obj={"predict": predict_flow_dict},
        )
        flow = json.loads(predict_flow)
        create_predict_flow_request = CreateFlowCls(
            nodes=flow,
            flow_name="{}_{}_{}_online_flow".format(
                settings.ENVIRONMENT, clustering_config.bk_biz_id, clustering_config.index_set_id
            ),
            project_id=self.conf.get("project_id"),
        )
        request_dict = self._set_username(create_predict_flow_request)
        result = BkDataDataFlowApi.create_flow(request_dict)
        clustering_config.predict_flow = predict_flow_dict
        clustering_config.predict_flow_id = result["flow_id"]
        clustering_config.model_output_rt = predict_flow_dict["clustering_predict"]["result_table_id"]
        #  填充签名字段打平节点-聚类结果表输出RT
        clustering_config.clustered_rt = predict_flow_dict["format_signature"]["result_table_id"]
        clustering_config.save()

        # 添加一步更新 update_model_instance
        data_processing_id_config = self.get_serving_data_processing_id_config(
            clustering_config.predict_flow['clustering_predict']["result_table_id"]
        )
        self.update_model_instance(model_instance_id=data_processing_id_config["id"])

        online_task = self.create_online_task(index_set_id=index_set_id)
        clustering_config.online_task_id = online_task["ci_id"]
        clustering_config.save()
        return result

    def update_predict_flow(self, index_set_id):
        """
        update_predict_flow
        @param index_set_id:
        @return:
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        if not clustering_config.predict_flow_id:
            logger.info(f"update predict flow not found: index_set_id -> {index_set_id}")
            return
        all_fields_dict = self.get_fields_dict(clustering_config=clustering_config)
        logger.info(f"update predict flow beginning: flow_id -> {clustering_config.predict_flow_id}")
        flow_id = clustering_config.predict_flow_id
        # 画布结构
        flow_graph = self.get_flow_graph(flow_id=flow_id)
        # 根据画布结构  更新节点
        nodes = flow_graph["nodes"]
        predict_flow_dict = asdict(
            self._init_predict_flow(
                result_table_id=clustering_config.bkdata_etl_result_table_id,
                model_id=clustering_config.model_id,
                model_release_id=self.get_latest_released_id(clustering_config.model_id),
                bk_biz_id=clustering_config.bk_biz_id,
                index_set_id=clustering_config.index_set_id,
                clustering_config=clustering_config,
                clustering_fields=all_fields_dict.get(clustering_config.clustering_fields),
            )
        )
        predict_flow = self._render_template(
            flow_mode=FlowMode.PREDICT_FLOW.value,
            render_obj={"predict": predict_flow_dict},
        )
        flow = json.loads(predict_flow)

        # 更新画布结构
        self.deal_predict_flow(nodes=nodes, flow=flow)

        # 重启 flow
        self.operator_flow(flow_id=flow_id, action=ActionEnum.RESTART)
        clustering_config.predict_flow = predict_flow_dict
        clustering_config.model_output_rt = predict_flow_dict["clustering_predict"]["result_table_id"]
        clustering_config.save()
        logger.info(f"update predict flow success: flow_id -> {clustering_config.predict_flow_id}")

    def _init_log_count_aggregation_flow(
        self,
        result_table_id: str,
        bk_biz_id: int,
        index_set_id: int,
    ):
        """
        初始化 create_log_count_aggregation_flow
        """

        # 参与聚类的 table_name  是 result_table_id去掉第一个_前的数字
        table_name_no_id = result_table_id.split("_", 1)[1]
        log_count_signatures = self.conf.get("log_count_signatures")  # 可能为空  如果为空 sql中的 where语句不要
        if not log_count_signatures:
            log_count_signatures_filter_rule = ""
        else:
            signatures = ", ".join(["'{}'".format(signature) for signature in log_count_signatures])
            log_count_signatures_filter_rule = " ".join(["WHERE signature NOT IN", "(", signatures, ")"])
        storage_type = self.conf.get("tspider_storage_type", TSPIDER_STORAGE_NODE_TYPE)
        log_count_aggregation_flow = LogCountAggregationFlowCls(
            log_count_signatures=log_count_signatures,
            table_name_no_id=table_name_no_id,
            result_table_id=result_table_id,
            log_count_aggregation=RealTimeCls(
                fields="",
                table_name=f"bklog_{index_set_id}_agg",
                result_table_id=f"{bk_biz_id}_bklog_{index_set_id}_agg",
                filter_rule=log_count_signatures_filter_rule,
            ),
            tspider_storage=TspiderStorageCls(
                cluster=self.conf.get("tspider_cluster"), expires=self.conf.get("log_count_tspider_expires")
            ),
            storage_type=storage_type,
            bk_biz_id=bk_biz_id,
            cluster=self.get_model_available_storage_cluster(),
        )

        return log_count_aggregation_flow

    def create_log_count_aggregation_flow(self, index_set_id):
        """
        create_log_count_aggregation_flow
        @param index_set_id:
        @return:
        """
        clustering_config = ClusteringConfig.get_by_index_set_id(index_set_id=index_set_id)
        result_table_id = clustering_config.predict_flow["clustering_predict"]["result_table_id"]
        log_count_aggregation_flow_dict = asdict(
            self._init_log_count_aggregation_flow(
                result_table_id=result_table_id,
                bk_biz_id=clustering_config.bk_biz_id,  # 当前业务id
                index_set_id=clustering_config.index_set_id,
            )
        )
        log_count_aggregation_flow = self._render_template(
            flow_mode=FlowMode.LOG_COUNT_AGGREGATION_FLOW.value,
            render_obj={"log_count_aggregation": log_count_aggregation_flow_dict},
        )
        flow = json.loads(log_count_aggregation_flow)
        create_log_count_aggregation_flow_request = CreateFlowCls(
            nodes=flow,
            flow_name="{}_{}_{}_agg_flow".format(
                settings.ENVIRONMENT, clustering_config.bk_biz_id, clustering_config.index_set_id
            ),
            project_id=self.conf.get("project_id"),
        )
        request_dict = self._set_username(create_log_count_aggregation_flow_request)
        result = BkDataDataFlowApi.create_flow(request_dict)

        clustering_config.log_count_aggregation_flow = log_count_aggregation_flow_dict
        clustering_config.log_count_aggregation_flow_id = result["flow_id"]
        clustering_config.new_cls_pattern_rt = log_count_aggregation_flow_dict["log_count_aggregation"][
            "result_table_id"
        ]
        clustering_config.save()
        return result

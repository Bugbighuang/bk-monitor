# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云 - 监控平台 (BlueKing - Monitor) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import base64
import copy
import json
import logging
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from elasticsearch_dsl import AttrDict

from bkmonitor.aiops.alert.utils import DimensionDrillManager, RecommendMetricManager
from bkmonitor.documents import AlertLog
from bkmonitor.utils import time_tools
from bkmonitor.utils.event_related_info import get_alert_relation_info
from bkmonitor.utils.time_tools import (
    hms_string,
    timestamp2datetime,
    utc2_str,
    utc2localtime,
)
from constants.action import ActionPluginType, ActionSignal, ConvergeType, NoticeWay
from constants.alert import (
    EVENT_STATUS_DICT,
    TARGET_DIMENSIONS,
    EventStatus,
    EventTargetType,
)
from constants.data_source import DATA_CATEGORY, DataSourceLabel, DataTypeLabel

from . import BaseContextObject

logger = logging.getLogger("fta_action.run")


class Alarm(BaseContextObject):
    """
    告警信息对象
    """

    @cached_property
    def id(self):
        if self.parent.alert:
            return self.parent.alert.id
        return ""

    @cached_property
    def name(self):
        if self.parent.alert:
            return self.parent.alert.alert_name
        return "--"

    @cached_property
    def level(self):
        return self.parent.alert_level

    @cached_property
    def level_name(self):
        """
        告警级别名称
        """
        return self.parent.level_name

    @cached_property
    def collect_count(self):
        """
        汇总的告警数量
        """
        return len(self.parent.alerts)

    @cached_property
    def is_no_data_alarm(self):
        """
        是否为无数据告警（监控专用）
        """
        return self.parent.alert.is_no_data()

    @cached_property
    def display_type(self):
        if self.is_no_data_alarm:
            return _("发生无数据告警")
        return _("发生告警")

    @cached_property
    def display_dimensions(self):
        """
        非目标维度
        """
        dedupe_fields = ["alert_name", "strategy_id", "target_type", "target", "bk_biz_id"]
        return {d.key: d for d in self.new_dimensions.values() if d.key not in dedupe_fields}

    @cached_property
    def display_targets(self):
        """
        监控目标
        """

        alerts = self.parent.alerts
        targets = []
        targets_dict = {}

        for alert in alerts:
            dimensions = {d["key"]: d for d in alert.target_dimensions}
            display_dimensions = []
            for key in TARGET_DIMENSIONS:
                if key not in dimensions or key == "bk_cloud_id":
                    # 云区域ID暂时去掉
                    continue
                display_value = dimensions[key].get("display_value") or dimensions[key]["value"]
                if display_value:
                    display_dimensions.append(str(display_value))

            if display_dimensions:
                target_display = ":".join(display_dimensions)
                if target_display in targets_dict:
                    targets_dict[target_display] += 1
                    continue
                targets_dict[target_display] = 1

        for target_display, count in targets_dict.items():
            if count > 1:
                targets.append("{}({})".format(target_display, count))
                continue
            targets.append(target_display)
        return targets

    @cached_property
    def target_string(self):
        """
        告警目标字符串
        """
        if not self.display_targets:
            return ""

        target_string = ",".join(self.display_targets)

        if self.parent.limit:
            limit_target_string = "{}...({})".format(self.display_targets[0], len(self.display_targets))
            if len(limit_target_string.encode("utf-8")) < len(target_string.encode("utf-8")):
                target_string = limit_target_string

        return target_string

    @cached_property
    def target_display(self):
        try:
            return getattr(self.parent.alert.event, "target", "")
        except BaseException as error:
            # 直接返回错误信息
            return str(error)

    @cached_property
    def dimensions(self):
        """
        维度字典
        """
        if self.parent.alert and self.parent.alert.origin_alarm:
            return {
                key: AttrDict(dimension)
                for key, dimension in self.parent.alert.origin_alarm["dimension_translation"].items()
            }
        return {}

    @cached_property
    def new_dimensions(self):
        """
        维度字典
        """
        strategy_dimensions = getattr(self.parent.action, "dimensions", [])
        if strategy_dimensions:
            # 默认从当前处理事件获取维度信息，如果不存在，则从alert获取
            return {
                dimension["key"]: dimension if isinstance(dimension, AttrDict) else AttrDict(dimension)
                for dimension in strategy_dimensions
            }
        if self.parent.alert:
            return {dimension.key: dimension for dimension in self.parent.alert.dimensions}
        return {}

    @cached_property
    def origin_dimensions(self):
        if self.parent.alert and self.parent.alert.origin_alarm:
            return self.parent.alert.origin_alarm["data"]["dimensions"]
        return {}

    @cached_property
    def dimension_string(self):
        """
        告警维度字符串
        """
        dimension_string = ",".join(self.dimension_string_list)

        if self.parent.limit:
            limit_dimension_string = "{}...".format(self.display_dimensions[0])
            if len(limit_dimension_string.encode("utf-8")) < len(dimension_string.encode("utf-8")):
                dimension_string = [limit_dimension_string]

        return dimension_string

    @cached_property
    def dimension_string_list(self):
        if not self.display_dimensions:
            return []

        # 拓扑维度特殊处理
        display_dimensions = copy.deepcopy(self.display_dimensions)
        dimension_string_list = []
        if self.parent.alert.agg_dimensions:
            # 当存在agg_dimensions的顺序列表是，直接使用
            for dimension_key in self.parent.alert.agg_dimensions:
                dimension_key = dimension_key[5:] if dimension_key.startswith("tags.") else dimension_key
                dimension = display_dimensions.pop(dimension_key, None)
                if not dimension:
                    continue
                dimension_string_list.append(
                    "{}={}".format(dimension.display_key or dimension_key, dimension.display_value or dimension.value)
                )
            # 如果维度不在agg dimensions中，直接添加在最后
            for dimension_key, dimension in display_dimensions.items():
                dimension_string_list.append(
                    "{}={}".format(dimension.display_key or dimension_key, dimension.display_value or dimension.value)
                )
        else:
            # 兼容不存在这一属性的值
            for d in self.display_dimensions.values():
                dimension_string_list.append("{}={}".format(d.display_key or d.key, d.display_value or d.value))
        return dimension_string_list

    @cached_property
    def chart_image(self):
        """
        邮件和微信出图
        """
        from .chart import get_chart_by_origin_alarm

        if not settings.GRAPH_RENDER_SERVICE_ENABLED or not self.parent.strategy.strategy_id:
            return None

        if not self.chart_image_enabled:
            # 不允许出图的策略，直接返回None
            return None

        if self.parent.converge_type != ConvergeType.ACTION:
            # 不允许
            return None

        # 无数据告警，不需要出图
        if self.is_no_data_alarm:
            return None

        strategy = self.parent.strategy
        alert = self.parent.alert
        chart = None
        if getattr(self.parent, "notice_way", None) == "wxwork-bot":
            title = f"{self.parent.strategy.name} - {self.parent.action.id}"
        else:
            title = strategy.items[0].name if strategy.items else "--"

        item = strategy.items[0]
        unify_query = item.query
        action_id = self.parent.action.id if self.parent.action else "None"

        # 无法出图的数据源
        if (
                (DataSourceLabel.BK_MONITOR_COLLECTOR, DataTypeLabel.EVENT) in item.data_source_types
                or (DataSourceLabel.BK_FTA, DataTypeLabel.ALERT) in item.data_source_types
                or (DataSourceLabel.BK_MONITOR_COLLECTOR, DataTypeLabel.ALERT) in item.data_source_types
        ):
            return

        try:
            # 数据维度过滤
            for data_source in unify_query.data_sources:
                try:
                    dimension_fields = alert.extra_info.origin_alarm.data.dimension_fields
                except AttributeError:
                    dimension_fields = data_source.group_by

                for key in self.origin_dimensions:
                    if key not in dimension_fields:
                        continue
                    data_source.filter_dict[key] = self.origin_dimensions[key]

            # 若告警状态为Abnormal，则alert_time为alert.latest_time，否则为alert.end_time
            if alert.status == EventStatus.ABNORMAL:
                alert_time = alert.latest_time
            else:
                alert_time = alert.end_time
            chart = get_chart_by_origin_alarm(
                strategy.items[0],
                timestamp2datetime(alert_time),
                title,
            )
        except Exception as e:
            logger.exception("action({}) of alert({}) create alarm chart error, {}".format(action_id, self.id, e))

        if chart:
            logger.info("action({}) of alert({}) create alarm chart success".format(action_id, self.id))

        return chart

    @cached_property
    def chart_image_enabled(self):
        """
        是否允许发送图片，默认为True
        """
        return self.parent.strategy.notice.get("options", {}).get("chart_image_enabled", True)

    @cached_property
    def chart_name(self):
        """
        图片名
        """
        if self.chart_image:
            return "alarm_chart_%s.png" % self.parent.action.id
        return ""

    @cached_property
    def attachments(self):
        attachment = []
        try:
            if self.chart_image:
                attachment.append(
                    {"filename": self.chart_name, "content_id": self.chart_name, "content": self.chart_image}
                )
        except BaseException as error:
            logger.exception(
                "get chart_image  of alert(%s) failed, error(%s)",
                self.parent.alert.id if self.parent.alert else "None",
                str(error),
            )

        return attachment

    @cached_property
    def time(self):
        if self.parent.alert:
            return utc2localtime(self.parent.alert.create_time)
        return "--"

    @cached_property
    def begin_time(self):
        return time_tools.utc2localtime(self.parent.alert.begin_time) if self.parent.alert else "--"

    @cached_property
    def duration(self):
        """
        事件持续时间
        """
        return self.parent.alert.duration or 60 if self.parent.alert else 0

    @cached_property
    def duration_string(self):
        """
        持续时间字符串
        :return:
        """
        if self.parent.alert.latest_time == self.parent.alert.first_anomaly_time:
            return None
        return hms_string(self.duration)

    @cached_property
    def current_value(self):
        """
        事件当前异常值
        """
        # 无数据告警不返回当前值
        if self.is_no_data_alarm:
            return None
        if self.parent.alert.status == EventStatus.RECOVERED:
            return getattr(self.parent.alert.extra_info, "recovery_value", None)
        try:
            return self.parent.anomaly_record.extra_info.origin_alarm.data.value
        except Exception as e:
            logger.info(
                "action(%s) get current value error: %s", self.parent.action.id if self.parent.action else "", e
            )
            return None

    @cached_property
    def detail_url(self):
        """
        告警详情链接, 告警url
        """
        if self.parent.is_external_channel:
            # 如果有channel信息，并且不是内部渠道，直接忽略链接
            return None
        if getattr(self.parent, "notice_way", None) in settings.ALARM_MOBILE_NOTICE_WAY and settings.ALARM_MOBILE_URL:
            url = settings.ALARM_MOBILE_URL
        else:
            url = settings.EVENT_CENTER_URL
        # collect_id 为兼容当前前监控版本的id
        return url.format(
            bk_biz_id=self.parent.business.bk_biz_id,
            action_id=self.parent.collect_id,
            collect_id=self.parent.collect_id,
        )

    @cached_property
    def example_detail_url(self):
        """代表单个告警的url"""
        if self.parent.is_external_channel:
            # 如果有channel信息，并且不是内部渠道，直接忽略链接
            return None

        if getattr(self.parent, "notice_way", None) in settings.ALARM_MOBILE_NOTICE_WAY and settings.ALARM_MOBILE_URL:
            url = settings.ALARM_MOBILE_URL
        else:
            url = settings.EVENT_CENTER_URL
        # collect_id 为兼容当前前监控版本的id
        return url.format(
            bk_biz_id=self.parent.business.bk_biz_id,
            action_id=self.parent.example_action.es_action_id,
            collect_id=self.parent.example_action.es_action_id,
        )

    @cached_property
    def quick_ack_url(self):
        if self.parent.is_external_channel:
            # 如果有channel信息，并且不是内部渠道，直接忽略链接
            return None
        return f"{self.detail_url}&batchAction=ack"

    @cached_property
    def quick_shield_url(self):
        if self.parent.is_external_channel:
            # 如果有channel信息，并且不是内部渠道，直接忽略链接
            return None
        if self.collect_count > 1:
            # 当有汇总的告警多余1个的时候，直接返回空
            return None
        return f"{self.detail_url}&batchAction=shield"

    @cached_property
    def quick_action_path(self):
        monitor_host = settings.BK_MONITOR_HOST
        if getattr(self.parent, "notice_way", None) in settings.ALARM_MOBILE_NOTICE_WAY and settings.ALARM_MOBILE_URL:
            mobile_host = urlparse(settings.ALARM_MOBILE_URL)
            if urlparse(monitor_host).hostname != mobile_host.hostname:
                # 如果域名不一致，则认为是微信端的独立域名
                monitor_host = "{}://{}".format(mobile_host.scheme, mobile_host.hostname)
            else:
                monitor_host = urljoin(monitor_host, "weixin/")
            return urljoin(monitor_host, "rest/v1/event/")
        else:
            return urljoin(monitor_host, "fta/alert/")

    @cached_property
    def notice_from(self):
        return _("蓝鲸监控")

    @cached_property
    def company(self):
        return ""

    @cached_property
    def data_source_name(self):
        """
        数据来源名称
        TODO: 手动执行产生的怎么算呢？
        """
        if not self.parent.strategy.id:
            return "--"
        try:
            item = self.parent.strategy.items[0]
        except BaseException:
            return "--"

        data_source_label = item.data_source_label
        data_type_label = item.data_type_label

        for category in DATA_CATEGORY:
            if category["data_source_label"] == data_source_label and category["data_type_label"] == data_type_label:
                return category["name"]

        return "{}_{}".format(data_source_label, data_type_label)

    @cached_property
    def target_type(self):
        """
        监控目标类型
        """
        if self.parent.alert:
            return self.parent.alert.event.target_type
        return "--"

    @cached_property
    def target_type_name(self):
        """
        监控目标名称
        """
        return {EventTargetType.HOST: "IP", EventTargetType.SERVICE: _("实例"), EventTargetType.TOPO: _("节点")}.get(
            self.target_type, self.target_type
        )

    @cached_property
    def related_info(self):
        """
        关联信息
        """
        return self.topo_related_info + self.log_related_info

    @cached_property
    def topo_related_info(self):
        # CMDB 拓扑层级相关联信息
        host = self.parent.target.host
        if host:
            return "{}({}) {}({})".format(_("集群"), host.set_string, _("模块"), host.module_string)
        return ""

    @cached_property
    def log_related_info(self):
        try:
            return get_alert_relation_info(self.parent.alert)
        except Exception as err:
            logger.exception("Get anomaly content err, msg is {}".format(err))
        return ""

    @cached_property
    def description(self):
        if self.end_description:
            # 如果有恢复信息，直接返回恢复内容
            return self.end_description

        duration_message = _("新告警")
        if self.duration_string:
            duration_message = _("已持续{}").format(self.duration_string)

        message = "{}, {}".format(duration_message, getattr(self.parent.alert.event, "description", ""))
        return message

    @cached_property
    def end_description(self):
        if self.parent.alert is None or self.parent.alert.status == EventStatus.ABNORMAL:
            return None
        return getattr(
            self.parent.alert.extra_info,
            "end_description",
            _("当前告警{}").format(EVENT_STATUS_DICT[self.parent.alert.status]),
        )

    @cached_property
    def callback_message(self):
        """
        接口回调数据
        :return:
        """
        alert = self.parent.alert
        if not alert:
            return json.dumps({})

        event = alert.event.to_dict()
        anomaly_record = {
            "anomaly_id": event["id"],
            "source_time": utc2_str(event["time"]),
            "create_time": utc2_str(event["create_time"]),
            "origin_alarm": event.get("extra_info", {}).get("origin_alarm", {}),
        }

        strategy = self.parent.strategy.config or alert.strategy or {}
        biz = self.parent.target.business

        data_source_names = {
            "bk_monitor": _("监控平台"),
            "bk_log_search": _("日志平台"),
            "bk_data": _("计算平台"),
            "custom": _("用户自定义"),
        }

        data_type_names = {
            "log": _("日志关键字"),
            "event": _("事件"),
            "time_series": _("时序"),
        }
        try:
            alert_relation_info = get_alert_relation_info(alert)
        except Exception as e:
            logger.exception(f"get alert[{alert.id}] relation info error: {e}")
            alert_relation_info = "Get relation info error, please contact the administrator"

        items = []
        agg_dimensions = []
        for item in strategy.get("items", []):
            for query_config in item["query_configs"]:
                items.append(
                    {
                        "metric_field": query_config["metric_id"].split(".")[-1],
                        "metric_field_name": item["name"],
                        "data_source_label": query_config["data_source_label"],
                        "data_source_name": data_source_names.get(query_config["data_source_label"], _("其他")),
                        "data_type_label": query_config["data_type_label"],
                        "data_type_name": data_type_names.get(query_config["data_type_label"], _("其他")),
                        "metric_id": query_config["metric_id"],
                    }
                )
                if len(query_config.get("agg_dimensions", [])) > len(agg_dimensions):
                    agg_dimensions = query_config.get("agg_dimensions", [])

        origin_alarm = alert.origin_alarm or {}

        if self.parent.action and self.parent.action.action_plugin["plugin_type"] == ActionPluginType.MESSAGE_QUEUE:
            # 消息队列有信号名称需要特殊处理
            signal_mapping = ActionSignal.MESSAGE_QUEUE_OPERATE_TYPE_MAPPING
        else:
            signal_mapping = ActionSignal.ACTION_SIGNAL_MAPPING

        action_signal = self.parent.action.signal if self.parent.action else ActionSignal.MANUAL
        action_info = {
            # 类型为操作时间的类型
            "type": signal_mapping.get(action_signal, ActionSignal.MANUAL),
            "scenario": strategy.get("scenario"),
            "bk_biz_id": event["bk_biz_id"],
            "bk_biz_name": biz.bk_biz_name,
            "event": {
                "id": alert.id,
                "event_id": alert.id,
                "is_shielded": alert.is_shielded,
                "begin_time": utc2_str(alert.begin_time),
                "create_time": utc2_str(alert.create_time),
                "end_time": utc2_str(alert.end_time) if alert.end_time else None,
                "level": self.parent.alert_level,
                "level_name": self.parent.level_name,
                "agg_dimensions": alert.agg_dimensions or agg_dimensions,
                "dimensions": origin_alarm.get("data", {}).get("dimensions"),
                "dimension_translation": origin_alarm.get("dimension_translation"),
            },
            "strategy": {
                "id": strategy.get("id") or None,
                "name": strategy.get("name") or "",
                "scenario": strategy.get("scenario") or None,
                "item_list": items,
            },
            "latest_anomaly_record": anomaly_record,
            "current_value": self.current_value,
            "description": self.description,
            "related_info": alert_relation_info,
            "labels": strategy.get("labels", []),
        }
        return json.dumps(action_info)

    @cached_property
    def alert_info(self):
        alert = self.parent.alert
        if not alert:
            return json.dumps({})

        alert_dict = copy.deepcopy(alert.to_dict())
        extra_info = alert_dict.pop("extra_info", None)
        alert_dict.update({"strategy": extra_info.get("strategy") if extra_info else {}})
        alert_dict["event"].pop("extra_info", None)
        alert_dict.update({"current_value": self.current_value, "description": self.description})
        return json.dumps(alert_dict)

    @cached_property
    def bkm_info(self):
        alert = self.parent.alert
        if not alert:
            return json.dumps({})

        event = alert.event.to_dict()
        try:
            extra_info = json.loads(event["extra_info"]["origin_alarm"]["data"]["values"]["extra_info"])
        except Exception:
            extra_info = {}
        return extra_info

    @cached_property
    def strategy_url(self):
        if self.parent.is_external_channel:
            return None

        if not self.parent.strategy.id:
            return ""

        return "{monitor_host}?bizId={bk_biz_id}#/strategy-config/detail/{strategy_id}".format(
            monitor_host=settings.BK_MONITOR_HOST,
            bk_biz_id=self.parent.alert.event.bk_biz_id,
            strategy_id=self.parent.strategy.id,
        )

    @cached_property
    def assignees(self):
        if not self.parent.alert:
            return ""
        return ",".join(self.parent.alert.assignee)

    @cached_property
    def ack_operator(self):
        if not self.parent.alert:
            return ""
        if len(self.ack_operators) == 1:
            return self.parent.alert.ack_operator
        else:
            return _("{}等").format(self.parent.alert.ack_operator)

    @cached_property
    def ack_operators(self):
        if not self.parent.alert:
            return ""
        return [alert.ack_operator for alert in self.parent.alerts if alert.ack_operator]

    @cached_property
    def ack_reason(self):
        if not self.parent.alert:
            return None

        ack_logs = AlertLog.get_ack_logs([alert.id for alert in self.parent.alerts])
        ack_messages = []
        for ack_log in ack_logs:
            ack_messages.append(ack_log.description)
        return ack_messages

    @cached_property
    def ack_title(self):
        if not self.collect_count:
            return None

        if self.collect_count == 1:
            return _("{ack_operator}已确认告警【{alert_name}】").format(
                ack_operator=self.ack_operator, alert_name=self.parent.alert.alert_name
            )

        return _("{ack_operator}已确认【{alert_name}】等{count}个告警").format(
            ack_operator=self.ack_operator, alert_name=self.parent.alert.alert_name, count=self.collect_count
        )

    @cached_property
    def latest_assign_group(self):
        if not self.parent.alert:
            return None
        extra_info = self.parent.alert.extra_info.to_dict()
        return extra_info.get("matched_rule_info", {}).get("group_info", {}).get("group_id")

    @cached_property
    def assign_detail(self):
        if not self.latest_assign_group:
            return None
        route_path = base64.b64encode(f"#/alarm-dispatch-config/{self.latest_assign_group}".encode("utf8")).decode(
            "utf8"
        )
        return urljoin(
            settings.BK_MONITOR_HOST,
            "route/?bizId={bk_biz_id}&route_path={route_path}".format(
                bk_biz_id=self.parent.business.bk_biz_id, route_path=route_path
            ),
        )

    @cached_property
    def is_abnormal(self):
        if self.parent.alert and self.parent.alert.status == EventStatus.ABNORMAL:
            return True
        return False

    @cached_property
    def anomaly_dimensions(self):
        if not self.parent.alert:
            return None
        try:
            result = DimensionDrillManager().fetch_aiops_result(self.parent.alert)
        except Exception as e:
            logger.exception(
                f"alert({self.parent.alert.id})-action("
                f"{self.parent.action.id if self.parent.action else ''}) aiops维度下钻接口请求异常: {e}"
            )
            return None

        anomaly_dimension_count = result["info"]["anomaly_dimension_count"]
        anomaly_dimension_value_count = result["info"]["anomaly_dimension_value_count"]
        return f"异常维度 {anomaly_dimension_count}，异常维度值 {anomaly_dimension_value_count}"

    @cached_property
    def recommended_metrics(self):
        if not self.parent.alert:
            return None
        try:
            result = RecommendMetricManager().fetch_aiops_result(self.parent.alert)
        except Exception as e:
            logger.exception(
                f"alert({self.parent.alert.id})-action("
                f"{self.parent.action.id if self.parent.action else ''}) aiops关联指标接口请求异常: {e}"
            )
            return None
        # 推荐指标维度数
        recommended_metric_dimension_count = result["info"]["recommended_metric_count"]
        # 推荐指标数
        recommended_metric_count = 0
        for recommended_metric in result["recommended_metrics"]:
            recommended_metric_dimension_count += len(recommended_metric.get("metrics", []))
        return f"{recommended_metric_count} 个指标,{recommended_metric_dimension_count} 个维度"

    @cached_property
    def link_layouts(self):
        if self.parent.notice_way != NoticeWay.WX_BOT or self.parent.example_action.signal not in [
            ActionSignal.ABNORMAL, ActionSignal.NO_DATA]:
            # 如果不是企业微信机器人，直接返回空
            # 如果不是异常告警，采用原来的模式发送通知
            return []
        if self.parent.converge_type == ConvergeType.CONVERGE and self.collect_count >= 1:
            # 如果是业务汇总，则不需要操作按钮
            return []

        if not self.detail_url:
            # 外部渠道不需要链接的，，则不需要操作按钮
            return []

        urls = [
            {"url": self.quick_ack_url, "name": _("告警确认")},
            {"url": self.detail_url, "button_style": {"type": "default", "fill": "follow"},
             "name": _("查看详情")},
        ]
        if self.quick_shield_url:
            urls.insert(1, {"url": self.quick_shield_url,
                            "name": _("告警屏蔽")})
        layouts = [
            {
                "type": "flex_layout",
                "components": [
                    {
                        "type": "button",
                        "text": urls[0]["name"],
                        "button_style": {"type": "colorful", "color": "yellow", "fill": "follow"},
                        "interaction": {"type": 2002, "data": {"url": urls[0]["url"]}},
                    },
                    {
                        "type": "button",
                        "text": urls[1]["name"],
                        "button_style": urls[1].get("button_style") or {"type": "colorful",
                                                                        "color": "yellow",
                                                                        "fill": "follow"},
                        "interaction": {"type": 2002, "data": {"url": urls[1]["url"]}},
                    },
                ],
                "style": {"vertical_line": ""},
                "num_inline": 2,
                "weight": [1, 1],
            }
        ]
        if len(urls) == 3:
            layouts.append(
                {
                    "type": "column_layout",
                    "components": [
                        {
                            "type": "button",
                            "text": urls[2]["name"],
                            "button_style": {"type": "default", "fill": "follow"},
                            "interaction": {"type": 2002, "data": {"url": urls[2]["url"]}},
                        }
                    ],
                }
            )
        return layouts
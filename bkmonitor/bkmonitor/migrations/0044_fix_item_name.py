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
# Generated by Django 1.11.23 on 2021-08-13 03:08
from __future__ import unicode_literals

from collections import defaultdict
from functools import reduce

from django.db import migrations
from django.db.models import Count, Q


def fix_item_name(apps, *args, **kwargs):
    """
    多指标策略指标信息修复
    """
    QueryConfigModel = apps.get_model("bkmonitor", "QueryConfigModel")
    ItemModel = apps.get_model("bkmonitor", "ItemModel")
    try:
        MetricListCache = apps.get_model("monitor_web", "MetricListCache")
    except (LookupError, KeyError):
        # worker 角色执行，无法加载monitor_web。
        print("当前执行migration 的角色是：worker，无法加载monitor_web，请先部署SaaS")
        return

    # 查询多指标策略
    query_config_counts = (
        QueryConfigModel.objects.all().values("strategy_id").annotate(total=Count("strategy_id")).filter(total__gt=1)
    )
    strategy_ids = [r["strategy_id"] for r in query_config_counts]

    if not strategy_ids:
        return

    items = ItemModel.objects.filter(strategy_id__in=strategy_ids)
    query_configs = QueryConfigModel.objects.filter(strategy_id__in=strategy_ids)

    # 查询指标名信息
    metric_infos = set()
    for query_config in query_configs:
        metric_infos.add((query_config.config["result_table_id"], query_config.config["metric_field"]))

    metrics = MetricListCache.objects.filter(
        data_source_label__in=["bk_monitor", "custom"], data_type_label="time_series"
    ).filter(reduce(lambda x, y: x | y, (Q(result_table_id=q[0], metric_field=q[1]) for q in metric_infos)))
    metric_names = {(metric.result_table_id, metric.metric_field): metric.metric_field_name for metric in metrics}

    # 按策略记录指标描述信息
    strategy_metric_descriptions = defaultdict(dict)
    for query_config in query_configs:
        metric_field_name = metric_names.get(
            (query_config.config["result_table_id"], query_config.config["metric_field"]),
            query_config.config["metric_field"],
        )
        metric_description = f"{query_config.config['agg_method'].upper()}({metric_field_name})"
        strategy_metric_descriptions[query_config.strategy_id][query_config.alias] = metric_description

    # 根据表达式渲染多指标描述
    for item in items:
        name = item.expression
        for alias, desc in strategy_metric_descriptions[item.strategy_id].items():
            name = name.replace(alias, desc)
        item.name = name
        item.save()


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0043_merge_20210813_1108"),
    ]

    operations = [migrations.RunPython(fix_item_name)]
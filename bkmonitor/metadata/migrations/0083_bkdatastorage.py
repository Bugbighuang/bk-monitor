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
# Generated by Django 1.11.23 on 2021-03-10 03:19


from django.db import migrations, models
import metadata.models.storage


class Migration(migrations.Migration):

    dependencies = [
        ("metadata", "0082_merge_20210122_1749"),
    ]

    operations = [
        migrations.CreateModel(
            name="BkDataStorage",
            fields=[
                ("table_id", models.CharField(max_length=128, primary_key=True, serialize=False, verbose_name="结果表名")),
                ("raw_data_id", models.IntegerField(default=-1, verbose_name="接入配置ID")),
                ("etl_json_config", models.TextField(verbose_name="清洗配置ID")),
                ("bk_data_result_table_id", models.CharField(max_length=64, verbose_name="计算平台的结果表名")),
            ],
            options={"verbose_name": "bkdata存储配置", "verbose_name_plural": "bkdata存储配置"},
            bases=(models.Model, metadata.models.storage.StorageResultTable),
        ),
    ]
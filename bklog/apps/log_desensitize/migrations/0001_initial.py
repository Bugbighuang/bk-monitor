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
# Generated by Django 3.2.15 on 2023-08-21 03:46

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DesensitizeConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('created_by', models.CharField(default='', max_length=32, verbose_name='创建者')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, null=True, verbose_name='更新时间')),
                ('updated_by', models.CharField(blank=True, default='', max_length=32, verbose_name='修改者')),
                ('index_set_id', models.IntegerField(db_index=True, verbose_name='索引集ID')),
                ('text_fields', models.JSONField(default=list, null=True, verbose_name='日志原文字段')),
            ],
            options={
                'verbose_name': '脱敏配置',
                'verbose_name_plural': '脱敏配置',
                'ordering': ('-updated_at',),
            },
        ),
        migrations.CreateModel(
            name='DesensitizeFieldConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('created_by', models.CharField(default='', max_length=32, verbose_name='创建者')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, null=True, verbose_name='更新时间')),
                ('updated_by', models.CharField(blank=True, default='', max_length=32, verbose_name='修改者')),
                ('index_set_id', models.IntegerField(db_index=True, verbose_name='索引集ID')),
                ('field_name', models.CharField(blank=True, default='', max_length=64, verbose_name='字段名称')),
                ('rule_id', models.IntegerField(db_index=True, default=0, verbose_name='脱敏规则ID')),
                ('operator', models.CharField(choices=[('mask_shield', '掩码屏蔽'), ('text_replace', '文本替换')], max_length=64, verbose_name='脱敏算子')),
                ('params', models.JSONField(default=dict, null=True, verbose_name='脱敏参数')),
                ('sort_index', models.IntegerField(default=0, null=True, verbose_name='优先级')),
            ],
            options={
                'verbose_name': '脱敏字段配置',
                'verbose_name_plural': '脱敏字段配置',
                'ordering': ('-updated_at',),
            },
        ),
        migrations.CreateModel(
            name='DesensitizeRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='创建时间')),
                ('created_by', models.CharField(default='', max_length=32, verbose_name='创建者')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, null=True, verbose_name='更新时间')),
                ('updated_by', models.CharField(blank=True, default='', max_length=32, verbose_name='修改者')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否删除')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='删除时间')),
                ('deleted_by', models.CharField(blank=True, max_length=32, null=True, verbose_name='删除者')),
                ('rule_name', models.CharField(max_length=128, verbose_name='脱敏规则名称')),
                ('operator', models.CharField(choices=[('mask_shield', '掩码屏蔽'), ('text_replace', '文本替换')], max_length=64, verbose_name='脱敏算子')),
                ('params', models.JSONField(default=dict, null=True, verbose_name='脱敏参数')),
                ('match_pattern', models.TextField(blank=True, default='', null=True, verbose_name='匹配模式')),
                ('space_uid', models.CharField(blank=True, default='', max_length=256, verbose_name='空间唯一标识')),
                ('is_public', models.BooleanField(default=False, verbose_name='是否为公共规则')),
                ('match_fields', models.JSONField(default=list, null=True, verbose_name='匹配字段名')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
            ],
            options={
                'verbose_name': '脱敏规则',
                'verbose_name_plural': '脱敏规则',
                'ordering': ('-updated_at',),
            },
        ),
    ]
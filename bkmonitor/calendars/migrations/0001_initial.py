# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-03-24 14:18
from __future__ import unicode_literals

import bkmonitor.utils.db.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CalendarItemModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_user', models.CharField(blank=True, default='', max_length=32, verbose_name='创建人')),
                ('create_time', models.IntegerField(blank=True, null=True, verbose_name='创建时间')),
                ('update_user', models.CharField(blank=True, default='', max_length=32, verbose_name='最后修改人')),
                ('update_time', models.IntegerField(blank=True, null=True, verbose_name='最后修改时间')),
                ('name', models.CharField(max_length=15, verbose_name='日历事项名称')),
                ('calendar_id', models.IntegerField(verbose_name='日历ID')),
                ('start_time', models.IntegerField(verbose_name='事项开始时间')),
                ('end_time', models.IntegerField(verbose_name='事项结束时间')),
                ('repeat', bkmonitor.utils.db.fields.JsonField(verbose_name='重复事项配置信息')),
                ('parent_id', models.IntegerField(blank=True, null=True, verbose_name='父事项ID')),
                ('time_zone', models.CharField(default='Asia/Shanghai', max_length=35, verbose_name='时区信息')),
            ],
            options={
                'verbose_name': '日历事项',
                'verbose_name_plural': '日历事项',
                'db_table': 'calendar_item',
            },
        ),
        migrations.CreateModel(
            name='CalendarModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_user', models.CharField(blank=True, default='', max_length=32, verbose_name='创建人')),
                ('create_time', models.IntegerField(blank=True, null=True, verbose_name='创建时间')),
                ('update_user', models.CharField(blank=True, default='', max_length=32, verbose_name='最后修改人')),
                ('update_time', models.IntegerField(blank=True, null=True, verbose_name='最后修改时间')),
                ('name', models.CharField(max_length=15, verbose_name='日历名称')),
                ('classify', models.CharField(choices=[('default', '内置'), ('custom', '自定义')], max_length=12, verbose_name='日历分类')),
                ('color', models.CharField(max_length=7, verbose_name='日历底色')),
            ],
            options={
                'verbose_name': '日历信息',
                'verbose_name_plural': '日历信息',
                'db_table': 'calendar',
            },
        ),
    ]
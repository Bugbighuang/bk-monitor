# Generated by Django 3.2.15 on 2023-08-21 06:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bkmonitor', '0141_init_result_table_data_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='metriclistcache',
            name='data_label',
            field=models.CharField(default='', max_length=256, verbose_name='db标识'),
        ),
    ]
# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-12-28 13:02
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0006_ip_log_functions'),
    ]

    operations = [
        migrations.AddField(
            model_name='user_job',
            name='error_log',
            field=models.CharField(default='NA', max_length=50),
        ),
    ]

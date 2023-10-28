/*
 * Tencent is pleased to support the open source community by making
 * 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community Edition) available.
 *
 * Copyright (C) 2021 THL A29 Limited, a Tencent company.  All rights reserved.
 *
 * 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community Edition) is licensed under the MIT License.
 *
 * License for 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community Edition):
 *
 * ---------------------------------------------------
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
 * to permit persons to whom the Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of
 * the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
 * THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
 * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */
import { Component, Mixins, Provide, ProvideReactive, Ref } from 'vue-property-decorator';
import { Route } from 'vue-router';

import authorityMixinCreate from '../../mixins/authorityMixin';
import { MANAGE_AUTH as GRAFANA_MANAGE_AUTH, VIEW_AUTH as GRAFANA_VIEW_AUTH } from '../grafana/authority-map';

import * as dataRetrievalAuthMap from './authority-map';
import DataRetrieval from './data-retrieval';

Component.registerHooks(['beforeRouteEnter']);
const authMap = {
  ...dataRetrievalAuthMap,
  GRAFANA_VIEW_AUTH,
  GRAFANA_MANAGE_AUTH
};

@Component
export default class IndexRetrieval extends Mixins(authorityMixinCreate(authMap)) {
  @Ref() dataRetrieval: DataRetrieval;
  @ProvideReactive('authority') authority: Record<string, boolean> = {};
  @Provide('handleShowAuthorityDetail') handleShowAuthorityDetail;
  @Provide('authorityMap') authorityMap;

  beforeRouteEnter(to: Route, from: Route, next: Function) {
    next((vm: IndexRetrieval) => {
      vm.dataRetrieval.handleBeforeRouteEnter(to, from);
    });
  }

  render() {
    return <DataRetrieval ref='dataRetrieval' />;
  }
}
/*
 * Tencent is pleased to support the open source community by making
 * 蓝鲸智云PaaS平台 (BlueKing PaaS) available.
 *
 * Copyright (C) 2021 THL A29 Limited, a Tencent company.  All rights reserved.
 *
 * 蓝鲸智云PaaS平台 (BlueKing PaaS) is licensed under the MIT License.
 *
 * License for 蓝鲸智云PaaS平台 (BlueKing PaaS):
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
/* eslint-disable no-new */
/* eslint-disable new-cap */
/*
 * @Date: 2021-06-14 20:39:08
 * @LastEditTime: 2021-06-23 16:03:29
 * @Description:
 */
// eslint-disable-next-line simple-import-sort/imports
import './public-path.ts';
import '../monitor-common/polyfill';
import Vue from 'vue';
import i18n from './i18n/i18n';

import './common/import-magicbox-ui';
import '../monitor-ui/directive/index';

import Api from '../monitor-api/api';
import { getContext } from '../monitor-api/modules/commons';
import { setVue } from '../monitor-api/utils/index';
import * as serviceWorker from '../monitor-common/service-worker/service-wroker';
import { getUrlParam, mergeSpaceList, setGlobalBizId } from '../monitor-common/utils';

import App from './pages/app';
import router from './router/router';
import Authority from './store/modules/authority';
import store from './store/store';

import '../monitor-static/icons/monitor-icons.css';
import './static/scss/global.scss';

Vue.config.devtools = process.env.NODE_ENV === 'development';
window.source_app = 'fta';
setVue(Vue);
if (process.env.NODE_ENV === 'development') {
  window.site_url = '/';
  const spaceUid = getUrlParam('space_uid');
  const bizId = getUrlParam('bizId')?.replace(/\//gim, '');
  getContext({
    space_uid: spaceUid || undefined,
    bk_biz_id: !spaceUid ? bizId || process.env.defaultBizId : undefined
  }).then(data => {
    Object.keys(data).forEach(key => {
      window[key.toLocaleLowerCase()] = data[key];
    });
    mergeSpaceList(window.space_list, window.bk_biz_list);
    window.username = window.uin;
    window.bk_log_search_url = window.bklogsearch_host;
    const bizId = setGlobalBizId();
    store.commit('app/SET_APP_STATE', {
      userName: data.UIN,
      bizId,
      bizList: window.space_list,
      csrfCookieName: data.CSRF_COOKIE_NAME,
      siteUrl: data.SITE_URL,
      bkUrl: data.BK_URL
    });
    // eslint-disable-next-line no-new
    new Vue({
      el: '#app',
      router,
      store,
      i18n,
      render: h => h(App)
    });
    Vue.prototype.$bus = new Vue();
    Vue.prototype.$api = Api;
    Vue.prototype.$authorityStore = Authority;
    serviceWorker.unregister();
  });
} else {
  mergeSpaceList(window.space_list, window.bk_biz_list);
  if (setGlobalBizId() !== false) {
    store.commit('app/SET_APP_STATE', {
      userName: window.user_name,
      bizId: window.cc_biz_id,
      bizList: window.space_list,
      csrfCookieName: window.csrf_cookie_name || '',
      siteUrl: window.site_url,
      bkUrl: window.bk_url
    });
    // eslint-disable-next-line no-new
    new Vue({
      el: '#app',
      router,
      store,
      i18n,
      render: h => h(App)
    });
    Vue.prototype.$bus = new Vue();
    Vue.prototype.$api = Api;
    Vue.prototype.$authorityStore = Authority;
    serviceWorker.register();
  }
}
import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',use:{baseURL:'http://127.0.0.1:5173',viewport:{width:1440,height:1000},trace:'retain-on-failure'},workers:1,timeout:60000,reporter:[['list'],['html',{open:'never'}]]});

import asyncio
from contextlib import asynccontextmanager
from urllib.parse import urlsplit
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.api.routes import router,TASKS
from app.core.config import ROOT
from app.database import store
from app.xdr.demo import seed
import os
import secrets

@asynccontextmanager
async def lifespan(app):
    store.init();seed()
    if not store.get('projects','demo-shop'):
        store.put('projects',{'id':'demo-shop','name':'Shop API · 演示项目','path':str(ROOT/'demo/shop'),'source':'demo','created_at':store.now(),'file_count':4,'last_scan_id':None})
    demo_project=store.get('projects','demo-shop')
    if demo_project and demo_project.get('source')=='demo' and demo_project['path']!=str(ROOT/'demo/shop'):
        demo_project['path']=str(ROOT/'demo/shop');store.put('projects',demo_project)
    for job in store.all_rows('investigations'):
        if job.get('remediation_pending'):
            job['remediation_pending']=False;store.put('investigations',job)
        if job['status'] in ('running','queued'):
            job['status']='interrupted';job['error']='上次服务停止时任务未完成，可重新启动调查';store.put('investigations',job)
    for repair in store.all_rows("remediations"):
        if repair["status"] in ("planning","validated","backed_up","deploying","verifying"):
            repair["status"]="recovery_required";repair["message"]="上次服务退出时修复未完成，请核实远程文件与备份，禁止自动重试";store.put("remediations",repair)
    from app.intelligence.service import scheduler
    from app.api.discovery import TASKS as DISCOVERY_TASKS
    for row in store.all_rows('discoveries'):
        if row['status'] in ('queued','running'):row['status']='interrupted';store.put('discoveries',row)
    for state in store.all_rows('ti_sync'):
        if state.get('status')=='running':
            state.update(status='interrupted',attempted_at=None,error='上次同步中断，将按启用的计划重新同步');store.put('ti_sync',state)
    ti_task=asyncio.create_task(scheduler())
    yield
    ti_task.cancel()
    for task in list(DISCOVERY_TASKS):task.cancel()
    await asyncio.gather(ti_task,*list(DISCOVERY_TASKS),return_exceptions=True)
    for task in list(TASKS): task.cancel()
    if TASKS: await asyncio.gather(*list(TASKS),return_exceptions=True)

app=FastAPI(title='Double Pupil · XDR × AI × Code',version='0.1.0',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=os.environ.get('SXF_ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(','))

@app.middleware('http')
async def local_boundary(request:Request,call_next):
    token=os.environ.get('SXF_DESKTOP_TOKEN')
    if token and not secrets.compare_digest(request.headers.get('x-sentinel-token',''),token):
        return JSONResponse({'detail':'Desktop session required'},status_code=403)
    # Single-operator loopback demo. Reject cross-site browser requests and mutations without a custom header.
    if request.url.path.startswith('/api'):
        origin=request.headers.get('origin')
        if request.headers.get('sec-fetch-site')=='cross-site' or (origin and urlsplit(origin).netloc!=request.headers.get('host')):
            return JSONResponse({'detail':'禁止跨域访问本地安全控制台'},status_code=403)
        if request.method in ('POST','PUT','PATCH','DELETE') and request.headers.get('x-sentinel-client')!='console':
            return JSONResponse({'detail':'缺少 X-Sentinel-Client: console 请求头'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff';response.headers['X-Frame-Options']='DENY';response.headers['Referrer-Policy']='no-referrer'
    if request.url.path.startswith('/api'): response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(ValueError)
async def value_error(request,exc):return JSONResponse({'detail':str(exc)},status_code=400)

app.include_router(router)

from app.api.management import router as management_router
app.include_router(management_router)

from app.api.discovery import router as discovery_router
from app.api.intelligence import router as intelligence_router
app.include_router(discovery_router)
app.include_router(intelligence_router)

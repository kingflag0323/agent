from fastapi import APIRouter,Query
from app.database import store
from app.intelligence import service
router=APIRouter(prefix='/api/intelligence')
@router.get('')
def listing(q:str='',provider:str='',page:int=Query(1,ge=1),page_size:int=Query(30,ge=1,le=100)):
    rows=[r for r in store.all_rows('intelligence') if (not provider or r['provider']==provider) and (not q or q.lower() in ' '.join(str(r.get(k,'')) for k in ('cve','title','description','vendor','product')).lower())]
    rows.sort(key=lambda r:(r['date'],r['id']),reverse=True)
    return {'items':rows[(page-1)*page_size:page*page_size],'total':len(rows),'sync':store.all_rows('ti_sync')}
@router.post('/sync')
async def sync():return await service.sync()

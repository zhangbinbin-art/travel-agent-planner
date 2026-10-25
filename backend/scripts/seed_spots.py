from core.database import SessionLocal
from models import Spot
db = SessionLocal()
if db.query(Spot).count() == 0:
    db.add_all([
        Spot(name='西湖景区', city='杭州', tags='自然风光', description='湖光山色，著名风景名胜区', score=4.9),
        Spot(name='故宫博物院', city='北京', tags='历史文化', description='明清两代皇家宫殿', score=4.9),
        Spot(name='外滩', city='上海', tags='城市观光', description='万国建筑博览群，夜景绝美', score=4.8),
    ])
    db.commit()
print(db.query(Spot).count())
db.close()

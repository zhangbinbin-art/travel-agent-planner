export const mockUser = {
  role: 'guest', // guest | user | admin
  username: ''
}

export const mockHotSpots = [
  { id: 1, name: '西湖景区', city: '杭州', tags: ['自然风光', '名胜古迹'], score: 4.9 },
  { id: 2, name: '故宫博物院', city: '北京', tags: ['历史文化', '博物馆'], score: 4.9 },
  { id: 3, name: '外滩', city: '上海', tags: ['城市观光', '夜景'], score: 4.8 }
]

export const mockHotPosts = [
  { id: 101, title: '杭州西湖三日游记', author: '旅行者A', heat: 1280 },
  { id: 102, title: '北京故宫拍摄指南', author: '旅行者B', heat: 980 },
  { id: 103, title: '上海外滩夜景打卡', author: '旅行者C', heat: 860 }
]

export const mockSpots = [
  { id: 1, name: '西湖景区', city: '杭州', tags: ['自然风光'], score: 4.9, desc: '著名的风景名胜区，湖光山色。' },
  { id: 2, name: '故宫博物院', city: '北京', tags: ['历史文化'], score: 4.9, desc: '明清两代皇家宫殿。' },
  { id: 3, name: '外滩', city: '上海', tags: ['城市观光'], score: 4.8, desc: '万国建筑博览群，夜景绝美。' },
  { id: 4, name: '灵隐寺', city: '杭州', tags: ['历史文化'], score: 4.8, desc: '著名古刹。' }
]

export const mockComments = [
  { id: 201, user: '用户1', content: '景色很美，值得一去！', score: 5 },
  { id: 202, user: '用户2', content: '人比较多，建议避开节假日。', score: 4 }
]

import api from './index'

export function toggleFollow(followUserId) {
  return api.post('/api/v1/user/follow', { follow_user_id: followUserId })
}

export function getFollowList(params) {
  return api.get('/api/v1/user/follow-list', { params })
}

export function getFansList(params) {
  return api.get('/api/v1/user/fans-list', { params })
}

export function getUserPosts(userId, params) {
  return api.get(`/api/v1/user/user-posts/${userId}`, { params })
}

export function sendMessage(data) {
  return api.post('/api/v1/user/message/send', data)
}

export function getChat(targetUserId, params) {
  return api.get(`/api/v1/user/message/chat/${targetUserId}`, { params })
}

// 用户主页信息（资料/帖子数/粉丝关注数/关注与拉黑状态）
export function getUserProfile(userId) {
  return api.get(`/api/v1/user/${userId}/profile`)
}

// 拉黑 / 解除拉黑（幂等切换）
export function toggleBlock(targetUserId) {
  return api.post(`/api/v1/user/block/${targetUserId}`)
}

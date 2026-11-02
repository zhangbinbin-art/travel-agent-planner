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

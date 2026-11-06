export const STAFF_ROLES = ['staff', 'admin']

export function homePathFor(user) {
  return user && STAFF_ROLES.includes(user.role) ? '/staff' : '/student'
}

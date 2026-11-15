export type Role = 'Mechanic' | 'Field Representative' | 'Dealer' | 'Administrator'
export const mechanics = [
  { name: 'Ravi Kumar', shop: 'Kumar Tyre Works', city: 'Kolkata', status: 'Active', tier: 'Skilled Mechanic', points: 1240, lastSeen: 'Today' },
  { name: 'Sanjay Das', shop: 'Das Puncture Centre', city: 'Durgapur', status: 'Pending review', tier: 'Registered Mechanic', points: 420, lastSeen: 'Yesterday' },
  { name: 'Amit Shaw', shop: 'Highway Wheel Care', city: 'Burdwan', status: 'Active', tier: 'Certified Mechanic', points: 2180, lastSeen: '2 days ago' },
  { name: 'Imran Ali', shop: 'Ali Auto Point', city: 'Howrah', status: 'Inactive', tier: 'Registered Mechanic', points: 180, lastSeen: '12 days ago' },
]
export const requests = [
  { id: 'TB-2048', mechanic: 'Ravi Kumar', item: 'Hydraulic tyre changer', date: '15 Nov 2026', status: 'Pending approval', value: '₹18,500' },
  { id: 'TB-2047', mechanic: 'Amit Shaw', item: 'Torque wrench set', date: '14 Nov 2026', status: 'Approved', value: '₹4,200' },
  { id: 'TB-2046', mechanic: 'Sanjay Das', item: 'Portable air compressor', date: '13 Nov 2026', status: 'Under review', value: '₹8,900' },
]
export const activities = [
  { title: 'New mechanic registration', detail: 'Ravi Kumar · Kolkata', time: '12 min ago', type: 'user' },
  { title: 'Fitment evidence submitted', detail: 'Recommendation #REC-1082', time: '48 min ago', type: 'verify' },
  { title: 'Tool request awaiting approval', detail: 'Hydraulic tyre changer · TB-2048', time: '1 hr ago', type: 'tool' },
  { title: 'Training certificate issued', detail: 'Amit Shaw · Tyre Safety Basics', time: '3 hrs ago', type: 'award' },
]

export const categories = [
  {
    id: 'compressors',
    name: 'Compressors',
    description: 'Screw air compressors that supply compressed air to the workshops and dry docks.',
  },
  {
    id: 'generators',
    name: 'Generators',
    description: 'Diesel generators that keep power running when the main supply goes down.',
  },
]

export const machines = [
  {
    id: 'compressor-1',
    categoryId: 'compressors',
    name: 'Compressor 1',
    type: 'Kaeser screw compressor',
    controller: 'Sigma Control 2',
    location: 'Main workshop',
    status: 'running',
    lastService: '2026-09-12',
    brief: 'Supplies compressed air to the main workshop. Pressure and temperature are within the normal range.',
  },
  {
    id: 'compressor-2',
    categoryId: 'compressors',
    name: 'Compressor 2',
    type: 'Kaeser screw compressor',
    controller: 'Sigma Control 2',
    location: 'Dry dock 1',
    status: 'warning',
    lastService: '2026-07-30',
    brief: 'Oil temperature has been slowly rising this week. Check the oil cooler and filter soon.',
  },
  {
    id: 'compressor-3',
    categoryId: 'compressors',
    name: 'Compressor 3',
    type: 'Kaeser screw compressor',
    controller: 'Sigma Control 2',
    location: 'Dry dock 2',
    status: 'stopped',
    lastService: '2026-06-18',
    brief: 'Stopped after a controller alarm. Waiting for a technician to check the error code.',
  },
  {
    id: 'generator-1',
    categoryId: 'generators',
    name: 'Generator 1',
    type: 'Diesel generator',
    controller: 'Auto start panel',
    location: 'Power house',
    status: 'running',
    lastService: '2026-08-22',
    brief: 'On standby and ready. Last weekly test run finished without any issues.',
  },
  {
    id: 'generator-2',
    categoryId: 'generators',
    name: 'Generator 2',
    type: 'Diesel generator',
    controller: 'Auto start panel',
    location: 'Power house',
    status: 'running',
    lastService: '2026-08-22',
    brief: 'On standby and ready. Fuel level is at 80 percent.',
  },
]

export function getCategory(categoryId) {
  return categories.find((category) => category.id === categoryId)
}

export function getMachinesByCategory(categoryId) {
  return machines.filter((machine) => machine.categoryId === categoryId)
}

export function getMachine(machineId) {
  return machines.find((machine) => machine.id === machineId)
}

export function countByStatus(list) {
  return list.reduce(
    (counts, machine) => {
      counts[machine.status] += 1
      return counts
    },
    { running: 0, warning: 0, stopped: 0 },
  )
}
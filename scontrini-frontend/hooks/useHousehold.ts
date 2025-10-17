'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'

export function useHousehold() {
  const { user } = useAuth()
  const [household, setHousehold] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [needsSetup, setNeedsSetup] = useState(false)

  useEffect(() => {
    async function checkHousehold() {
      if (!user) {
        setLoading(false)
        return
      }

      try {
        // Chiama API route per controllare household
        const response = await fetch('/api/household/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ userId: user.id })
        })

        const data = await response.json()

        if (data.hasHousehold) {
          setHousehold(data.household)
          setNeedsSetup(false)
        } else {
          setNeedsSetup(true)
        }

        setLoading(false)
      } catch (err) {
        console.error('Error checking household:', err)
        setLoading(false)
      }
    }

    checkHousehold()
  }, [user])

  const createHousehold = async (name: string) => {
    if (!user) throw new Error('User not authenticated')

    try {
      // Chiama API route per creare household
      const response = await fetch('/api/household/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          userId: user.id,
          householdName: name 
        })
      })

      const data = await response.json()

      if (!data.success) {
        throw new Error(data.error || 'Failed to create household')
      }

      setHousehold(data.household)
      setNeedsSetup(false)

      return data.household
    } catch (err) {
      console.error('Error creating household:', err)
      throw err
    }
  }

  return {
    household,
    loading,
    needsSetup,
    createHousehold,
  }
}
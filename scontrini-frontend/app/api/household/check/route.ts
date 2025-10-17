import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  {
    auth: {
      autoRefreshToken: false,
      persistSession: false
    }
  }
)

export async function POST(request: Request) {
  try {
    const { userId } = await request.json()

    if (!userId) {
      return NextResponse.json(
        { error: 'Missing userId' },
        { status: 400 }
      )
    }

    // Controlla se l'utente ha già un household
    const { data: membership, error } = await supabaseAdmin
      .from('household_members')
      .select('household_id, households(*)')
      .eq('user_id', userId)
      .single()

    if (error || !membership) {
      return NextResponse.json({ 
        hasHousehold: false,
        household: null 
      })
    }

    return NextResponse.json({ 
      hasHousehold: true,
      household: membership.households 
    })

  } catch (error: any) {
    console.error('Error checking household:', error)
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    )
  }
}
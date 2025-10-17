import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'

// Client con SERVICE_ROLE_KEY per bypassare RLS
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
    const { userId, householdName } = await request.json()

    if (!userId || !householdName) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    // 1. Crea household
    const { data: household, error: householdError } = await supabaseAdmin
      .from('households')
      .insert({ name: householdName })
      .select()
      .single()

    if (householdError) {
      console.error('Error creating household:', householdError)
      return NextResponse.json(
        { error: householdError.message },
        { status: 500 }
      )
    }

    // 2. Crea membership (owner)
    const { error: memberError } = await supabaseAdmin
      .from('household_members')
      .insert({
        household_id: household.id,
        user_id: userId,
        role: 'owner'
      })

    if (memberError) {
      console.error('Error creating membership:', memberError)
      // Rollback: elimina household se membership fallisce
      await supabaseAdmin.from('households').delete().eq('id', household.id)
      
      return NextResponse.json(
        { error: memberError.message },
        { status: 500 }
      )
    }

    return NextResponse.json({ 
      success: true, 
      household 
    })

  } catch (error: any) {
    console.error('Unexpected error:', error)
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    )
  }
}
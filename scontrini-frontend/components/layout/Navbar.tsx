'use client'

import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { LogOut, User } from 'lucide-react'
import Link from 'next/link'

export function Navbar() {
  const { user, signOut } = useAuth()

  return (
    <nav className="border-b bg-white">
      <div className="container mx-auto px-4">
        <div className="flex h-16 items-center justify-between">
          {/* Logo & Brand */}
          <Link href="/dashboard" className="flex items-center space-x-2">
            <span className="text-2xl">🧾</span>
            <span className="text-xl font-bold">Scontrini</span>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-6">
            <Link 
              href="/dashboard" 
              className="text-sm font-medium hover:text-primary transition-colors"
            >
              Dashboard
            </Link>
            <Link 
              href="/upload" 
              className="text-sm font-medium hover:text-primary transition-colors"
            >
              Carica Scontrino
            </Link>
            <Link 
              href="/receipts" 
              className="text-sm font-medium hover:text-primary transition-colors"
            >
              Storico
            </Link>
          </div>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <div className="hidden md:flex items-center space-x-2 text-sm text-muted-foreground">
              <User className="h-4 w-4" />
              <span>{user?.email}</span>
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => signOut()}
              className="flex items-center space-x-2"
            >
              <LogOut className="h-4 w-4" />
              <span>Esci</span>
            </Button>
          </div>
        </div>
      </div>
    </nav>
  )
}
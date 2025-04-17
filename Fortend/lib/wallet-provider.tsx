"use client"

import type React from "react"
import { createContext, useContext, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useToast } from "@/components/ui/use-toast"
import { api } from "@/lib/api-client"

// Types
export interface Wallet {
  address: string
  publicKey: string
  balance: number
}

interface WalletContextType {
  wallet: Wallet | null
  isLoading: boolean
  error: string | null
  createWallet: () => Promise<any>
  importWallet: (privateKey: string) => Promise<any>
  logout: () => void
  refreshWallet: () => Promise<void>
}

// Create context
const WalletContext = createContext<WalletContextType | undefined>(undefined)

// Provider component
export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [wallet, setWallet] = useState<Wallet | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()
  const { toast } = useToast()

  // Initialize wallet from localStorage on mount
  useEffect(() => {
    const initWallet = async () => {
      setIsLoading(true)
      try {
        // Only run on client side
        if (typeof window !== "undefined") {
          const privateKey = localStorage.getItem("privateKey")
          if (privateKey) {
            await fetchWalletInfo()
          }
        }
      } catch (err: any) {
        console.error("Failed to initialize wallet:", err)
        setError("Failed to initialize wallet")
      } finally {
        setIsLoading(false)
      }
    }

    initWallet()
  }, [])

  // Fetch wallet info from API
  const fetchWalletInfo = async () => {
    try {
      const walletData = await api.wallet.getInfo()
      setWallet(walletData)
      return walletData
    } catch (err: any) {
      console.error("Error fetching wallet info:", err)

      // If we get a 401, the private key is invalid or expired
      if (err.response?.status === 401) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("privateKey")
        }
        setWallet(null)
        router.push("/wallet/import")
        toast({
          title: "Session expired",
          description: "Please import your wallet again",
          variant: "destructive",
        })
      }
      throw err
    }
  }

  // Create a new wallet
  const createWallet = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.wallet.create()
      const { privateKey, ...walletData } = response

      // Store private key in localStorage
      if (typeof window !== "undefined") {
        localStorage.setItem("privateKey", privateKey)
      }

      // Set wallet data in state
      setWallet(walletData)

      toast({
        title: "Wallet created",
        description: "Your new wallet has been created successfully",
      })

      router.push("/dashboard")
      return response
    } catch (err: any) {
      console.error("Error creating wallet:", err)
      setError("Failed to create wallet")
      toast({
        title: "Error",
        description: "Failed to create wallet",
        variant: "destructive",
      })
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  // Import an existing wallet
  const importWallet = async (privateKey: string) => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.wallet.import(privateKey)

      // Store private key in localStorage
      if (typeof window !== "undefined") {
        localStorage.setItem("privateKey", privateKey)
      }

      // Set wallet data in state
      setWallet(response)

      toast({
        title: "Wallet imported",
        description: "Your wallet has been imported successfully",
      })

      router.push("/dashboard")
      return response
    } catch (err: any) {
      console.error("Error importing wallet:", err)
      setError("Failed to import wallet. Invalid private key.")
      toast({
        title: "Error",
        description: "Failed to import wallet. Invalid private key.",
        variant: "destructive",
      })
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  // Logout - clear wallet data and redirect to home
  const logout = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("privateKey")
    }
    setWallet(null)
    router.push("/")
    toast({
      title: "Logged out",
      description: "You have been logged out successfully",
    })
  }

  // Refresh wallet data
  const refreshWallet = async () => {
    try {
      await fetchWalletInfo()
      toast({
        title: "Refreshed",
        description: "Wallet data has been refreshed",
      })
    } catch (err: any) {
      toast({
        title: "Error",
        description: "Failed to refresh wallet data",
        variant: "destructive",
      })
    }
  }

  return (
    <WalletContext.Provider
      value={{
        wallet,
        isLoading,
        error,
        createWallet,
        importWallet,
        logout,
        refreshWallet,
      }}
    >
      {children}
    </WalletContext.Provider>
  )
}

// Hook for using the wallet context
export function useWallet() {
  const context = useContext(WalletContext)
  if (context === undefined) {
    throw new Error("useWallet must be used within a WalletProvider")
  }
  return context
}

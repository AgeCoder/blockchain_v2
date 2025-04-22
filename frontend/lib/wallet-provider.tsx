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
        if (typeof window !== "undefined") {
          const encryptedPrivateKey = localStorage.getItem("privateKey")
          if (encryptedPrivateKey) {
            console.log(encryptedPrivateKey);

            // Decrypt the private key (use a static passphrase for now; in production, prompt user)
            const privateKey = await decryptPrivateKey(encryptedPrivateKey, "aligthage.online.v2");
            await importWallet(privateKey)
          } else {
            setWallet(null)
          }
        }
      } catch (err: any) {
        console.error("Failed to initialize wallet:", err)
        setError("Failed to initialize wallet. Please import or create a wallet.")
        toast({
          title: "Initialization Error",
          description: "Failed to initialize wallet. Please try again.",
          variant: "destructive",
        })
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
      if (err.response?.status === 400 && err.response?.data?.error === "Wallet not initialized") {
        // Wallet not initialized on backend, clear local state
        if (typeof window !== "undefined") {
          localStorage.removeItem("privateKey")
        }
        setWallet(null)
        router.push("/wallet/import")
        toast({
          title: "Wallet Error",
          description: "Wallet not initialized. Please import your wallet again.",
          variant: "destructive",
        })
      } else if (err.response?.status === 401) {
        // Invalid or expired private key
        if (typeof window !== "undefined") {
          localStorage.removeItem("privateKey")
        }
        setWallet(null)
        router.push("/wallet/import")
        toast({
          title: "Session Expired",
          description: "Please import your wallet again.",
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

      // Encrypt private key before storing
      if (typeof window !== "undefined") {
        const encryptedPrivateKey = await encryptPrivateKey(privateKey, "aligthage.online.v2");
        localStorage.setItem("privateKey", encryptedPrivateKey)
      }

      // Set wallet data in state
      setWallet(walletData)

      toast({
        title: "Wallet Created",
        description: "Your new wallet has been created successfully.",
      })

      // router.push("/dashboard")
      return response
    } catch (err: any) {
      console.error("Error creating wallet:", err)
      setError("Failed to create wallet")
      toast({
        title: "Error",
        description: err.response?.data?.error || "Failed to create wallet.",
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
      // Validate private key format (basic check)
      if (!privateKey || typeof privateKey !== "string" || privateKey.trim() === "") {
        throw new Error("Invalid private key format")
      }

      const response = await api.wallet.import(privateKey)
      const { privateKey: returnedPrivateKey, ...walletData } = response

      // Encrypt private key before storing
      if (typeof window !== "undefined") {
        const encryptedPrivateKey = await encryptPrivateKey(privateKey, "aligthage.online.v2");
        localStorage.setItem("privateKey", encryptedPrivateKey)
      }

      // Set wallet data in state
      setWallet(walletData)

      toast({
        title: "Wallet Imported",
        description: "Your wallet has been imported successfully.",
      })

      // router.push("/dashboard")
      return response
    } catch (err: any) {
      console.error("Error importing wallet:", err)
      setError("Failed to import wallet. Invalid private key.")
      toast({
        title: "Error",
        description: err.response?.data?.error || "Failed to import wallet. Invalid private key.",
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
      title: "Logged Out",
      description: "You have been logged out successfully.",
    })
  }

  // Refresh wallet data
  const refreshWallet = async () => {
    try {
      await fetchWalletInfo()
      toast({
        title: "Refreshed",
        description: "Wallet data has been refreshed.",
      })
    } catch (err: any) {
      toast({
        title: "Error",
        description: "Failed to refresh wallet data.",
        variant: "destructive",
      })
    }
  }

  // Utility to derive an encryption key from a passphrase
  async function deriveKey(passphrase: string): Promise<CryptoKey> {
    const encoder = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
      "raw",
      encoder.encode(passphrase),
      { name: "PBKDF2" },
      false,
      ["deriveKey"]
    );
    return crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: encoder.encode("wallet-salt"),
        iterations: 100000,
        hash: "SHA-256",
      },
      keyMaterial,
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"]
    );
  }

  // Encrypt private key
  async function encryptPrivateKey(privateKey: string, passphrase: string): Promise<string> {
    const encoder = new TextEncoder();
    const key = await deriveKey(passphrase);
    const iv = crypto.getRandomValues(new Uint8Array(12)); // 12-byte IV for AES-GCM
    const encrypted = await crypto.subtle.encrypt(
      {
        name: "AES-GCM",
        iv,
      },
      key,
      encoder.encode(privateKey)
    );
    // Combine IV and encrypted data, encode as base64
    const ivAndEncrypted = new Uint8Array([...iv, ...new Uint8Array(encrypted)]);
    return btoa(String.fromCharCode(...ivAndEncrypted));
  }

  // Decrypt private key
  async function decryptPrivateKey(encryptedKey: string, passphrase: string): Promise<string> {
    const decoder = new TextDecoder();
    const key = await deriveKey(passphrase);
    const ivAndEncrypted = Uint8Array.from(atob(encryptedKey), (c) => c.charCodeAt(0));
    const iv = ivAndEncrypted.slice(0, 12);
    const encrypted = ivAndEncrypted.slice(12);
    const decrypted = await crypto.subtle.decrypt(
      {
        name: "AES-GCM",
        iv,
      },
      key,
      encrypted
    );
    return decoder.decode(decrypted);
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
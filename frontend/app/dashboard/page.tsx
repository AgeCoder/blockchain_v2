"use client"

import React, { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  ArrowUpRight,
  ArrowDownLeft,
  RefreshCw,
  Copy,
  Clock,
  ChevronRight,
  AlertCircle,
  Wallet,
  Send,
  History,
} from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useToast } from "@/components/ui/use-toast"
import { useWallet } from "@/lib/wallet-provider"
import { api } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"
import { LoadingSpinner } from "@/components/ui/loading-spinner"
import { Badge } from "@/components/ui/badge"
import type { Transaction } from "@/types/transaction"

interface SendForm {
  recipient: string
  amount: string
  fee: string
}

export default function DashboardPage() {
  const { wallet, isLoading, refreshWallet } = useWallet()
  const router = useRouter()
  const { toast } = useToast()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoadingTx, setIsLoadingTx] = useState(true)
  const [sendForm, setSendForm] = useState<SendForm>({
    recipient: "",
    amount: "",
    fee: "0.0001", // Default fee from backend DEFAULT_FEE_RATE
  })
  const [sendingTx, setSendingTx] = useState(false)
  const [formError, setFormError] = useState("")

  // Calculate mining fee
  const calculateFee = useCallback((amount: number): number => {
    const baseFee = 0.0001 // MIN_FEE from backend
    const size = 250 // BASE_TX_SIZE from backend
    const feeRate = Number.parseFloat(sendForm.fee) || 0.0001 // DEFAULT_FEE_RATE
    return Math.max(baseFee, size * feeRate)
  }, [sendForm.fee])

  useEffect(() => {
    if (!isLoading && !wallet) {
      router.push("/wallet/import")
    } else if (wallet) {
      fetchTransactions()
    }
  }, [wallet, isLoading, router])

  const fetchTransactions = async () => {
    if (!wallet?.address) return

    setIsLoadingTx(true)
    try {
      const txData = await api.transactions.getByAddress(wallet.address)
      const formattedTx: Transaction[] = txData.map((tx: any) => {
        const isSend = tx.input.address === wallet.address
        const otherAddr = isSend
          ? Object.keys(tx.output).find((addr) => addr !== wallet.address) || ""
          : tx.input.address
        const amount = isSend ? tx.input.amount - (tx.output[wallet.address] || 0) : tx.output[wallet.address] || 0

        return {
          id: tx.id,
          type: isSend ? "send" : "receive",
          amount,
          timestamp: new Date(tx.timestamp / 1_000_000).toISOString(),
          status: tx.status || "confirmed", // Default to confirmed for mined txs
          address: otherAddr,
          blockHeight: tx.blockHeight,
          fee: tx.fee || 0,
        }
      })

      setTransactions(formattedTx.slice(0, 10)) // Show latest 10
    } catch (error) {
      console.error("Error fetching transactions:", error)
      toast({
        title: "Error",
        description: "Failed to load transactions",
        variant: "destructive",
      })
    } finally {
      setIsLoadingTx(false)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await refreshWallet()
      await fetchTransactions()
      toast({
        title: "Refreshed",
        description: "Wallet and transactions updated",
      })
    } catch (error) {
      console.error("Error refreshing:", error)
      toast({
        title: "Error",
        description: "Failed to refresh data",
        variant: "destructive",
      })
    } finally {
      setIsRefreshing(false)
    }
  }

  const copyAddress = () => {
    if (wallet?.address) {
      navigator.clipboard.writeText(wallet.address)
      toast({
        title: "Copied!",
        description: "Wallet address copied to clipboard",
      })
    }
  }

  const handleSendTransaction = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError("")

    // Validation
    if (!sendForm.recipient.trim()) {
      setFormError("Recipient address is required")
      return
    }

    const amount = Number.parseFloat(sendForm.amount)
    if (isNaN(amount) || amount <= 0) {
      setFormError("Amount must be a positive number")
      return
    }

    const fee = Number.parseFloat(sendForm.fee)
    if (isNaN(fee) || fee < 0.0001) {
      setFormError("Fee must be at least 0.0001")
      return
    }

    if (wallet && amount + fee > wallet.balance) {
      setFormError("Insufficient balance (including fee)")
      return
    }

    setSendingTx(true)
    try {
      await api.wallet.transact(sendForm.recipient, amount, { fee })
      toast({
        title: "Transaction Sent",
        description: `Sent ${amount.toFixed(6)} coins to ${sendForm.recipient} with ${fee.toFixed(6)} fee`,
      })

      setSendForm({ recipient: "", amount: "", fee: "0.0001" })
      await refreshWallet()
      await fetchTransactions()
    } catch (error) {
      console.error("Transaction error:", error)
      setFormError("Transaction failed. Invalid address or network issue.")
    } finally {
      setSendingTx(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8" role="region" aria-label="Loading wallet dashboard">
        <Skeleton className="h-12 w-48 mb-6" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-[200px] rounded-lg" />
          <Skeleton className="h-[300px] rounded-lg md:col-span-2" />
          <Skeleton className="h-[400px] rounded-lg md:col-span-3" />
        </div>
      </div>
    )
  }

  if (!wallet) return null

  const estimatedFee = sendForm.amount ? calculateFee(Number.parseFloat(sendForm.amount)).toFixed(6) : "0.000100"

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="container mx-auto px-4 py-8"
        role="main"
        aria-label="Wallet Dashboard"
      >
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <h1 className="text-3xl font-bold">Wallet Dashboard</h1>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            aria-label="Refresh wallet data"
          >
            {isRefreshing ? (
              <LoadingSpinner className="mr-2 h-4 w-4" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Refresh
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Wallet Info Card */}
          <motion.div
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.3 }}
            className="md:col-span-1"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wallet className="h-5 w-5" />
                  Wallet Info
                </CardTitle>
                <CardDescription>Your blockchain wallet details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-xs text-muted-foreground">Address</Label>
                  <div className="flex items-center mt-1 gap-2">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="bg-muted p-2 rounded text-xs font-mono truncate flex-1">
                          {wallet.address}
                        </span>
                      </TooltipTrigger>
                      <TooltipContent>{wallet.address}</TooltipContent>
                    </Tooltip>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={copyAddress}
                      aria-label="Copy wallet address"
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">Balance</Label>
                  <p className="text-2xl font-bold">{wallet.balance.toFixed(6)} Coins</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Send Transaction Card */}
          <motion.div
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="md:col-span-2"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Send className="h-5 w-5" />
                  Send Transaction
                </CardTitle>
                <CardDescription>Transfer coins with customizable fees</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSendTransaction} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="recipient">Recipient Address</Label>
                    <Input
                      id="recipient"
                      placeholder="Enter recipient address"
                      value={sendForm.recipient}
                      onChange={(e) => setSendForm({ ...sendForm, recipient: e.target.value })}
                      aria-describedby="recipient-error"
                    />
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="amount">Amount (Coins)</Label>
                      <Input
                        id="amount"
                        type="number"
                        step="0.000001"
                        min="0.000001"
                        placeholder="0.000000"
                        value={sendForm.amount}
                        onChange={(e) => setSendForm({ ...sendForm, amount: e.target.value })}
                        aria-describedby="amount-error"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="fee">Transaction Fee (Coins/Byte)</Label>
                      <Input
                        id="fee"
                        type="number"
                        step="0.000001"
                        min="0.0001"
                        placeholder="0.000100"
                        value={sendForm.fee}
                        onChange={(e) => setSendForm({ ...sendForm, fee: e.target.value })}
                        aria-describedby="fee-error"
                      />
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Estimated Fee: {estimatedFee} Coins
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="ml-2 underline cursor-help">How is this calculated?</span>
                      </TooltipTrigger>
                      <TooltipContent>
                        Fee = max(MIN_FEE, BASE_TX_SIZE * Fee Rate)
                        <br />
                        MIN_FEE: 0.0001, BASE_TX_SIZE: 250 bytes
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <AnimatePresence>
                    {formError && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="bg-destructive/10 p-3 rounded-md flex items-start"
                        role="alert"
                        aria-live="assertive"
                      >
                        <AlertCircle className="h-5 w-5 text-destructive mr-2 mt-0.5" />
                        <p className="text-sm text-destructive">{formError}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </form>
              </CardContent>
              <CardFooter className="flex gap-4">
                <Button
                  onClick={handleSendTransaction}
                  disabled={sendingTx || !sendForm.recipient || !sendForm.amount || !sendForm.fee}
                  className="flex-1"
                  aria-label="Send transaction"
                >
                  {sendingTx ? (
                    <>
                      <LoadingSpinner className="mr-2 h-4 w-4" />
                      Sending...
                    </>
                  ) : (
                    "Send Transaction"
                  )}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setSendForm({ recipient: "", amount: "", fee: "0.0001" })}
                  disabled={sendingTx}
                  aria-label="Reset form"
                >
                  Reset
                </Button>
              </CardFooter>
            </Card>
          </motion.div>

          {/* Recent Transactions Card */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="md:col-span-3"
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <History className="h-5 w-5" />
                    Recent Transactions
                  </CardTitle>
                  <CardDescription>Your latest blockchain activity</CardDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push("/transactions")}
                  aria-label="View all transactions"
                >
                  View All <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                {isLoadingTx ? (
                  <div className="space-y-4">
                    {[...Array(4)].map((_, i) => (
                      <Skeleton key={i} className="h-20 w-full" />
                    ))}
                  </div>
                ) : transactions.length > 0 ? (
                  <div className="space-y-4">
                    {transactions.map((tx, index) => (
                      <motion.div
                        key={tx.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.1 }}
                        className="flex items-center justify-between p-4 rounded-lg border hover:bg-muted"
                        role="article"
                        tabIndex={0}
                        onClick={() => router.push(`/transactions/${tx.id}`)}
                        onKeyDown={(e) => e.key === "Enter" && router.push(`/transactions/${tx.id}`)}
                      >
                        <div className="flex items-center gap-4">
                          {tx.type === "send" ? (
                            <div className="bg-orange-100 dark:bg-orange-900 p-2 rounded-full">
                              <ArrowUpRight className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                            </div>
                          ) : (
                            <div className="bg-green-100 dark:bg-green-900 p-2 rounded-full">
                              <ArrowDownLeft className="h-5 w-5 text-green-600 dark:text-green-400" />
                            </div>
                          )}
                          <div>
                            <p className="font-medium capitalize">{tx.type}</p>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <p className="text-xs text-muted-foreground truncate max-w-[200px]">
                                  {tx.address}
                                </p>
                              </TooltipTrigger>
                              <TooltipContent>{tx.address}</TooltipContent>
                            </Tooltip>
                            <p className="text-xs text-muted-foreground">
                              Block #{tx.blockHeight} • Fee: {tx?.fee?.toFixed(6)}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p
                            className={`font-medium ${tx.type === "send"
                              ? "text-orange-600 dark:text-orange-400"
                              : "text-green-600 dark:text-green-400"
                              }`}
                          >
                            {tx.type === "send" ? "-" : "+"}
                            {tx.amount.toFixed(6)} Coins
                          </p>
                          <div className="flex items-center justify-end text-xs text-muted-foreground">
                            <Clock className="h-3 w-3 mr-1" />
                            {formatDistanceToNow(new Date(tx.timestamp), { addSuffix: true })}
                            <Badge
                              variant="outline"
                              className={`ml-2 capitalize ${tx.status === "confirmed"
                                ? "border-green-500 text-green-600 dark:text-green-400"
                                : tx.status === "pending"
                                  ? "border-yellow-500 text-yellow-600 dark:text-yellow-400"
                                  : "border-red-500 text-red-600 dark:text-red-400"
                                }`}
                            >
                              {tx.status}
                            </Badge>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-10">
                    <p className="text-muted-foreground text-lg">No Transactions Yet</p>
                    <p className="text-sm mt-2">
                      Send or receive coins to start your transaction history
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </motion.div>
    </TooltipProvider>
  )
}
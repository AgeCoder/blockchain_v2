"use client"

import type React from "react"
import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowUpRight, ArrowDownLeft, RefreshCw, Copy, Clock, ChevronRight, AlertCircle } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/components/ui/use-toast"
import { useWallet } from "@/lib/wallet-provider"
import { api } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"
import { LoadingSpinner } from "@/components/ui/loading-spinner"
import type { Transaction } from "@/types/transaction"

export default function DashboardPage() {
  const { wallet, isLoading, refreshWallet } = useWallet()
  const router = useRouter()
  const { toast } = useToast()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isLoadingTx, setIsLoadingTx] = useState(true)
  const [sendForm, setSendForm] = useState({
    recipient: "",
    amount: "",
  })
  const [sendingTx, setSendingTx] = useState(false)
  const [formError, setFormError] = useState("")

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

      // Format transactions
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
          timestamp: new Date(tx.timestamp / 1000000).toISOString(),
          status: tx.status || "pending",
          address: otherAddr,
          blockHeight: tx.blockHeight,
        }
      })

      setTransactions(formattedTx.slice(0, 5)) // Show only the latest 5
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
        description: "Dashboard data has been updated",
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
        description: "Address copied to clipboard",
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

    if (wallet && amount > wallet.balance) {
      setFormError("Insufficient balance")
      return
    }

    setSendingTx(true)
    try {
      await api.wallet.transact(sendForm.recipient, amount)

      toast({
        title: "Transaction sent",
        description: `Successfully sent ${amount} coins to ${sendForm.recipient}`,
      })

      // Reset form
      setSendForm({
        recipient: "",
        amount: "",
      })

      // Refresh wallet and transactions
      await refreshWallet()
      await fetchTransactions()
    } catch (error) {
      console.error("Transaction error:", error)
      setFormError("Transaction failed. Please try again.")
    } finally {
      setSendingTx(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Skeleton className="h-[200px] rounded-lg" />
          <Skeleton className="h-[200px] rounded-lg md:col-span-2" />
          <Skeleton className="h-[300px] rounded-lg md:col-span-3" />
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="container mx-auto px-4 py-8"
    >
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
        <h1 className="text-3xl font-bold">Wallet Dashboard</h1>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing} className="mt-2 md:mt-0">
          {isRefreshing ? <LoadingSpinner className="mr-2" /> : <RefreshCw className="h-4 w-4 mr-2" />}
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Wallet Info Card */}
        <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.3 }}>
          <Card>
            <CardHeader>
              <CardTitle>Wallet Info</CardTitle>
              <CardDescription>Your blockchain wallet details</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-xs text-muted-foreground">Address</Label>
                <div className="flex items-center mt-1">
                  <div className="bg-muted p-2 rounded text-xs font-mono truncate flex-1">{wallet?.address}</div>
                  <Button variant="ghost" size="icon" onClick={copyAddress} aria-label="Copy address">
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Balance</Label>
                <p className="text-2xl font-bold">{wallet?.balance.toFixed(2)}</p>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Send Transaction Card */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="md:col-span-2"
        >
          <Card>
            <CardHeader>
              <CardTitle>Send Transaction</CardTitle>
              <CardDescription>Transfer coins to another wallet</CardDescription>
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
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="amount">Amount</Label>
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="0.00"
                    value={sendForm.amount}
                    onChange={(e) => setSendForm({ ...sendForm, amount: e.target.value })}
                  />
                </div>
                <AnimatePresence>
                  {formError && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="bg-destructive/10 p-3 rounded-md flex items-start"
                    >
                      <AlertCircle className="h-5 w-5 text-destructive mr-2 mt-0.5" />
                      <p className="text-sm text-destructive">{formError}</p>
                    </motion.div>
                  )}
                </AnimatePresence>
              </form>
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleSendTransaction}
                disabled={sendingTx || !sendForm.recipient || !sendForm.amount}
                className="w-full"
              >
                {sendingTx ? (
                  <>
                    <LoadingSpinner className="mr-2" />
                    Sending...
                  </>
                ) : (
                  "Send Transaction"
                )}
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
                <CardTitle>Recent Transactions</CardTitle>
                <CardDescription>Your latest blockchain transactions</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={() => router.push("/transactions")}>
                View All <ChevronRight className="ml-1 h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              {isLoadingTx ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-16 w-full" />
                  ))}
                </div>
              ) : transactions.length > 0 ? (
                <div className="space-y-3">
                  {transactions.map((tx, index) => (
                    <motion.div
                      key={tx.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.1 }}
                      className="flex items-center justify-between p-3 rounded-lg border"
                    >
                      <div className="flex items-center">
                        {tx.type === "send" ? (
                          <div className="bg-orange-100 dark:bg-orange-900 p-2 rounded-full mr-3">
                            <ArrowUpRight className="h-5 w-5 text-orange-600 dark:text-orange-400" />
                          </div>
                        ) : (
                          <div className="bg-green-100 dark:bg-green-900 p-2 rounded-full mr-3">
                            <ArrowDownLeft className="h-5 w-5 text-green-600 dark:text-green-400" />
                          </div>
                        )}
                        <div>
                          <p className="font-medium">{tx.type === "send" ? "Sent" : "Received"}</p>
                          <p className="text-xs text-muted-foreground truncate max-w-[150px]">{tx.address}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p
                          className={`font-medium ${tx.type === "send" ? "text-orange-600 dark:text-orange-400" : "text-green-600 dark:text-green-400"}`}
                        >
                          {tx.type === "send" ? "-" : "+"}
                          {tx.amount.toFixed(2)}
                        </p>
                        <div className="flex items-center text-xs text-muted-foreground">
                          <Clock className="h-3 w-3 mr-1" />
                          {formatDistanceToNow(new Date(tx.timestamp), { addSuffix: true })}
                          <span
                            className={`ml-2 px-1.5 py-0.5 rounded-full text-[10px] uppercase
                            ${tx.status === "confirmed"
                                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
                                : tx.status === "pending"
                                  ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300"
                                  : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
                              }`}
                          >
                            {tx.status}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground">No transactions yet</p>
                  <p className="text-sm mt-2">Send or receive coins to see your transaction history</p>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  )
}

"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { ArrowUpRight, ArrowDownLeft, RefreshCw, Clock, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { useToast } from "@/components/ui/use-toast"
import { useWallet } from "@/lib/wallet-provider"
import { api } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"

interface Transaction {
  id: string
  type: "send" | "receive"
  amount: number
  timestamp: string
  status: "pending" | "confirmed" | "failed"
  address: string
  blockHeight?: number
}

export default function TransactionsPage() {
  const { wallet, isLoading: walletLoading } = useWallet()
  const router = useRouter()
  const { toast } = useToast()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [pendingTransactions, setPendingTransactions] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [activeTab, setActiveTab] = useState("all")

  useEffect(() => {
    if (!walletLoading && !wallet) {
      router.push("/wallet/import")
    } else if (wallet) {
      fetchTransactions()
    }
  }, [wallet, walletLoading])

  const fetchTransactions = async () => {
    if (!wallet?.address) return

    setIsLoading(true)
    try {
      // Fetch user transactions
      const txResponse = await api.transactions.getByAddress(wallet.address)

      // Format transactions
      const formattedTx: Transaction[] = txResponse.map((tx: any) => {
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

      setTransactions(formattedTx)

      // Fetch pending transactions
      const pendingResponse = await api.transactions.getPending()
      setPendingTransactions(pendingResponse.data)
    } catch (error) {
      console.error("Error fetching transactions:", error)
      toast({
        title: "Error",
        description: "Failed to load transactions",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await fetchTransactions()
      toast({
        title: "Refreshed",
        description: "Transactions have been refreshed",
      })
    } finally {
      setIsRefreshing(false)
    }
  }

  const filteredTransactions = () => {
    if (activeTab === "all") return transactions
    if (activeTab === "sent") return transactions.filter((tx) => tx.type === "send")
    if (activeTab === "received") return transactions.filter((tx) => tx.type === "receive")
    if (activeTab === "pending") return transactions.filter((tx) => tx.status === "pending")
    return transactions
  }

  if (walletLoading || isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-24" />
        </div>
        <Skeleton className="h-12 w-full mb-6" />
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
        <h1 className="text-3xl font-bold">Transactions</h1>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing} className="mt-2 md:mt-0">
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <Tabs defaultValue="all" className="mb-6" onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="sent">Sent</TabsTrigger>
          <TabsTrigger value="received">Received</TabsTrigger>
          <TabsTrigger value="pending">Pending</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="space-y-4">
        {filteredTransactions().length > 0 ? (
          filteredTransactions().map((tx) => (
            <Card key={tx.id}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
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
                      <p className="text-xs text-muted-foreground truncate max-w-[200px]">{tx.address}</p>
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
                        className={`ml-2 px-1.5 py-0.5 rounded-full text-[10px] uppercase ${tx.status === "confirmed"
                          ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300"
                          : tx.status === "pending"
                            ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300"
                            : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300"
                          }`}
                      >
                        {tx.status}
                      </span>
                      {tx.blockHeight && <span className="ml-2 text-xs">Block #{tx.blockHeight}</span>}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No transactions found</p>
            {activeTab !== "all" && (
              <Button variant="link" onClick={() => setActiveTab("all")} className="mt-2">
                View all transactions
              </Button>
            )}
          </div>
        )}
      </div>

      {activeTab === "pending" && pendingTransactions?.length > 0 && (
        <div className="mt-8">
          <h2 className="text-xl font-bold mb-4">Pending Transaction Pool</h2>
          <Card>
            <CardHeader>
              <CardTitle>Global Pending Transactions</CardTitle>
              <CardDescription>Transactions waiting to be included in a block</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {pendingTransactions.map((tx) => (
                  <div key={tx.id} className="p-3 border rounded-lg flex justify-between items-center">
                    <div>
                      <p className="font-mono text-sm truncate max-w-[200px]">{tx.id}</p>
                      <div className="flex items-center text-xs text-muted-foreground mt-1">
                        <span>From: </span>
                        <span className="font-mono truncate max-w-[150px] ml-1">{tx.input.address}</span>
                      </div>
                    </div>
                    <Button variant="ghost" size="sm">
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

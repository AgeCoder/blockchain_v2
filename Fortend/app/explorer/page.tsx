"use client"

import React, { useEffect, useState, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import { Search, Database, Clock, ArrowDown, ChevronRight, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"
import { useToast } from "@/components/ui/use-toast"
import { debounce } from "lodash"

// Types aligned with backend schema
interface Block {
  hash: string
  height: number
  timestamp: number
  data: any[]
  nonce: number
  last_hash: string
  difficulty: number
  version: number
  merkle_root: string
  tx_count: number
}

interface BlockchainResponse {
  chain: Block[]
  utxo_set: Record<string, any>
  current_height: number
}

const useDebounce = <T extends (...args: any[]) => any>(callback: T, delay: number) => {
  return useMemo(() => debounce(callback, delay), [callback, delay])
}

export default function ExplorerPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(true)
  const [blocks, setBlocks] = useState<Block[]>([])
  const [blockchainLength, setBlockchainLength] = useState(0)
  const [searchQuery, setSearchQuery] = useState("")
  const [currentRange, setCurrentRange] = useState({ start: 0, end: 5 })
  const [loadingMore, setLoadingMore] = useState(false)
  const [searchResults, setSearchResults] = useState<Block[]>([])
  const [isSearching, setIsSearching] = useState(false)

  const fetchBlockchainData = useCallback(async () => {
    setIsLoading(true)
    try {
      const lengthResponse = await api.blockchain.getLength()
      setBlockchainLength(lengthResponse.length)
      await fetchBlocksRange(0, 5)
    } catch (error) {
      console.error("Error fetching blockchain data:", error)
      toast({
        title: "Error",
        description: "Failed to load blockchain data",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  const fetchBlocksRange = useCallback(
    async (start: number, end: number) => {
      try {
        const response = await api.blockchain.getRange(start, end)
        if (start === 0) {
          setBlocks(response)
        } else {
          setBlocks((prev) => [...prev, ...response])
        }
        setCurrentRange({ start, end })
      } catch (error) {
        console.error("Error fetching blocks range:", error)
        toast({
          title: "Error",
          description: "Failed to load blocks",
          variant: "destructive",
        })
      }
    },
    [toast]
  )

  const loadMoreBlocks = useCallback(async () => {
    if (loadingMore || currentRange.end >= blockchainLength) return
    setLoadingMore(true)
    try {
      const newStart = currentRange.end
      const newEnd = Math.min(newStart + 5, blockchainLength)
      await fetchBlocksRange(newStart, newEnd)
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, currentRange.end, blockchainLength, fetchBlocksRange])

  const handleSearch = useCallback(
    async (query: string) => {
      if (!query.trim()) {
        setSearchResults([])
        setIsSearching(false)
        return
      }
      setIsSearching(true)
      try {
        const response = await api.blockchain.getAll()
        const blocks = response.chain
        const results = blocks.filter(
          (block: Block) =>
            block.hash.includes(query) ||
            block.height.toString() === query ||
            block.last_hash.includes(query)
        ).slice(0, 5) // Limit to 5 results
        setSearchResults(results)
      } catch (error) {
        console.error("Error searching blocks:", error)
        toast({
          title: "Error",
          description: "Failed to search blocks",
          variant: "destructive",
        })
      } finally {
        setIsSearching(false)
      }
    },
    [toast]
  )

  const debouncedSearch = useDebounce(handleSearch, 300)

  const viewBlockDetails = useCallback(
    (block: Block) => {
      router.push(`/explorer/block/${block.height}`)
    },
    [router]
  )

  useEffect(() => {
    fetchBlockchainData()
  }, [fetchBlockchainData])

  useEffect(() => {
    debouncedSearch(searchQuery)
  }, [searchQuery, debouncedSearch])

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8" role="region" aria-label="Loading blockchain explorer">
        <div className="mb-6">
          <Skeleton className="h-12 w-full max-w-md" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-[200px]" />
          ))}
        </div>
      </div>
    )
  }

  const displayedBlocks = searchResults.length > 0 ? searchResults : blocks
  const latestDifficulty = blocks.length > 0 ? blocks[0].difficulty : 3

  return (
    <div className="container mx-auto px-4 py-8" role="main" aria-label="Blockchain Explorer">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <h1 className="text-3xl font-bold">Blockchain Explorer</h1>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSearch(searchQuery)
          }}
          className="w-full md:w-auto"
        >
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search by block hash, height, or previous hash..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 w-full md:w-[300px]"
              aria-label="Search blocks"
            />
          </div>
        </form>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl">{blockchainLength}</CardTitle>
            <CardDescription>Total Blocks</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl">
              {blocks.reduce((acc, block) => acc + block.data.length, 0)}
            </CardTitle>
            <CardDescription>Total Transactions</CardDescription>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-2xl">{latestDifficulty}</CardTitle>
            <CardDescription>Current Difficulty</CardDescription>
          </CardHeader>
        </Card>
      </div>

      <h2 className="text-2xl font-bold mb-4">Latest Blocks</h2>

      {isSearching ? (
        <div className="flex justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6" role="list">
          {displayedBlocks.map((block) => (
            <Card
              key={block.hash}
              className="overflow-hidden"
              role="listitem"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && viewBlockDetails(block)}
            >
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center">
                      <Database className="h-5 w-5 mr-2" aria-hidden="true" />
                      Block #{block.height}
                    </CardTitle>
                    <CardDescription className="flex items-center mt-1">
                      <Clock className="h-3 w-3 mr-1" aria-hidden="true" />
                      {formatDistanceToNow(new Date(block.timestamp / 1_000_000), { addSuffix: true })}
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => viewBlockDetails(block)}
                    className="text-xs"
                    aria-label={`View details for block ${block.height}`}
                  >
                    Details <ChevronRight className="ml-1 h-3 w-3" aria-hidden="true" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Hash:</span>
                    <span className="font-mono truncate max-w-[400px]">{block.hash}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Previous Hash:</span>
                    <span className="font-mono truncate max-w-[400px]">{block.last_hash}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Transactions:</span>
                    <span>{block.data.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Nonce:</span>
                    <span>{block.nonce}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {currentRange.end < blockchainLength && !searchResults.length && (
        <div className="flex justify-center mt-8">
          <Button
            variant="outline"
            onClick={loadMoreBlocks}
            disabled={loadingMore}
            className="gap-2"
            aria-label="Load more blocks"
          >
            {loadingMore ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Loading...
              </>
            ) : (
              <>
                <ArrowDown className="h-4 w-4" aria-hidden="true" />
                Load More Blocks
              </>
            )}
          </Button>
        </div>
      )}
    </div>
  )
}
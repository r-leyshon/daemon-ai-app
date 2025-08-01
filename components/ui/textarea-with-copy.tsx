import * as React from "react"
import { Copy, Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "./button"
import { Textarea } from "./textarea"

interface TextareaWithCopyProps extends Omit<React.ComponentProps<typeof Textarea>, 'onCopy'> {
  onCopyText?: (text: string) => void
}

const TextareaWithCopy = React.forwardRef<HTMLTextAreaElement, TextareaWithCopyProps>(
  ({ className, onCopyText, ...props }, ref) => {
    const [copied, setCopied] = React.useState(false)

    const handleCopy = async () => {
      const textToCopy = props.value as string || ""
      
      try {
        await navigator.clipboard.writeText(textToCopy)
        setCopied(true)
        onCopyText?.(textToCopy)
        
        // Reset the copied state after 2 seconds
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        console.error('Failed to copy text: ', err)
        // Fallback for older browsers
        const textArea = document.createElement('textarea')
        textArea.value = textToCopy
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    }

    return (
      <div className="relative">
        <Textarea
          ref={ref}
          className={cn("pr-12", className)}
          {...props}
        />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-8 w-8 p-0 hover:bg-gray-100"
          onClick={handleCopy}
          title={copied ? "Copied!" : "Copy to clipboard"}
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-600" />
          ) : (
            <Copy className="h-4 w-4 text-gray-500" />
          )}
        </Button>
      </div>
    )
  }
)

TextareaWithCopy.displayName = "TextareaWithCopy"

export { TextareaWithCopy } 
// Groups order items by parent_order_item_id (add-ons nest under their
// container/parent) for a clearer receipt-style listing — mirrors
// bot/src/order_items.py so the bot and the app profile show the same
// structure. Uses the existing formatPriceK ("15к") compact price notation.
import { formatPriceK } from '@/utils/price'

export interface OrderItemLike {
    order_item_id: number
    product_id: number
    product_name?: string | null
    unit_price: number
    quantity: number
    parent_order_item_id?: number | null
}

export type OrderItemRow =
    | { type: 'flat'; key: number; text: string }
    | { type: 'group'; key: number; header: string; children: { key: number; text: string }[] }

const cleanName = (name: string) => name.replace(/\r\n|\r|\n/g, ' ').trim()

export function groupOrderItems(
    items: OrderItemLike[],
    productFallback: (productId: number) => string
): OrderItemRow[] {
    const childrenByParent = new Map<number, OrderItemLike[]>()
    for (const item of items) {
        if (item.parent_order_item_id != null) {
            const list = childrenByParent.get(item.parent_order_item_id) ?? []
            list.push(item)
            childrenByParent.set(item.parent_order_item_id, list)
        }
    }

    const rows: OrderItemRow[] = []
    for (const item of items) {
        if (item.parent_order_item_id != null) continue // rendered under its parent below

        const name = cleanName(item.product_name || productFallback(item.product_id))
        const kids = childrenByParent.get(item.order_item_id)

        if (kids && kids.length > 0) {
            const ownTotal = item.unit_price * item.quantity
            const header = ownTotal === 0 ? name : `${item.quantity} × ${name} - ${formatPriceK(ownTotal)}`
            rows.push({
                type: 'group',
                key: item.order_item_id,
                header,
                children: kids.map((child) => {
                    const childName = cleanName(child.product_name || productFallback(child.product_id))
                    return {
                        key: child.order_item_id,
                        text: `${child.quantity} × ${childName} - ${formatPriceK(child.unit_price * child.quantity)}`,
                    }
                }),
            })
        } else {
            rows.push({
                type: 'flat',
                key: item.order_item_id,
                text: `${item.quantity} × ${name} - ${formatPriceK(item.unit_price * item.quantity)}`,
            })
        }
    }
    return rows
}

import ReasoningPanel from '../operations/ReasoningPanel'
import type { OperationsSnapshot } from '../../types/operations'

export default function ReasoningPage({ snapshot }: { snapshot: OperationsSnapshot | null }) {
  return <ReasoningPanel snapshot={snapshot} />
}

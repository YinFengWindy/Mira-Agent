/**
 * Legacy icon entry point. The drawings now live in `shared/ui/icons`
 * (the Shiori custom set); these aliases keep every pre-restyle call
 * site rendering the new artwork without changes.
 */
export {
  ArrowClockwiseIcon as ResetIcon,
  CaretLeftIcon as BackIcon,
  CaretRightIcon,
  CheckIcon as SaveIcon,
  CircleNotchIcon as SpinnerIcon,
  CopyIcon,
  FileTextIcon as DocumentIcon,
  LocateIcon,
  PaperPlaneTiltIcon as SendIcon,
  PlusIcon,
  PromptLibraryIcon,
  QuoteIcon,
  SmileyIcon,
  UploadSimpleIcon as UploadIcon,
  XIcon as CloseIcon,
  XIcon as DeleteIcon,
} from "./ui/icons";

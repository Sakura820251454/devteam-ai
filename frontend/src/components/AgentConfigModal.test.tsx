import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AgentConfigModal from '@/components/AgentConfigModal'

describe('AgentConfigModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onAgentsConfigured: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('modal is not rendered when isOpen is false', () => {
    render(<AgentConfigModal {...defaultProps} isOpen={false} />)
    expect(screen.queryByText('配置 Agent 团队')).not.toBeInTheDocument()
  })

  it('modal is rendered when isOpen is true', () => {
    render(<AgentConfigModal {...defaultProps} />)
    expect(screen.getByText('配置 Agent 团队')).toBeInTheDocument()
  })

  it('shows two mode tabs: preset and custom', () => {
    render(<AgentConfigModal {...defaultProps} />)
    expect(screen.getByText('预设角色')).toBeInTheDocument()
    expect(screen.getByText('自定义角色')).toBeInTheDocument()
  })

  describe('Preset Mode', () => {
    it('displays all 6 preset roles', () => {
      render(<AgentConfigModal {...defaultProps} />)
      expect(screen.getByText('产品经理')).toBeInTheDocument()
      expect(screen.getByText('架构师')).toBeInTheDocument()
      expect(screen.getByText('后端开发')).toBeInTheDocument()
      expect(screen.getByText('前端开发')).toBeInTheDocument()
      expect(screen.getByText('测试工程师')).toBeInTheDocument()
      expect(screen.getByText('运维工程师')).toBeInTheDocument()
    })

    it('can select a role', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      const pmCard = screen.getByText('产品经理').closest('button')
      fireEvent.click(pmCard!)
      
      expect(screen.getByText('已选择 (1)')).toBeInTheDocument()
    })

    it('can select multiple roles', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('产品经理').closest('button')!)
      fireEvent.click(screen.getByText('后端开发').closest('button')!)
      
      expect(screen.getByText('已选择 (2)')).toBeInTheDocument()
    })

    it('can deselect a role', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      const pmCard = screen.getByText('产品经理').closest('button')
      fireEvent.click(pmCard!)
      expect(screen.getByText('已选择 (1)')).toBeInTheDocument()
      
      fireEvent.click(pmCard!)
      expect(screen.getByText('已选择 (0)')).toBeInTheDocument()
    })

    it('can add extra responsibilities to selected role', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('产品经理').closest('button')!)
      
      const addResponsibility = screen.getByText('+ 添加职责')
      fireEvent.click(addResponsibility)
      
      const devTag = screen.getByText('+ 后端')
      fireEvent.click(devTag)
      
      expect(screen.getByText('后端')).toBeInTheDocument()
    })

    it('can remove selected role from list', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('产品经理').closest('button')!)
      expect(screen.getByText('已选择 (1)')).toBeInTheDocument()
      
      fireEvent.click(screen.getByText('移除'))
      expect(screen.getByText('已选择 (0)')).toBeInTheDocument()
    })
  })

  describe('Custom Mode', () => {
    it('switches to custom mode when tab clicked', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('自定义角色'))
      
      expect(screen.getByText('创建自定义角色')).toBeInTheDocument()
    })

    it('can create a custom role with name and description', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('自定义角色'))
      
      const nameInput = screen.getByPlaceholderText('例如：数据分析师')
      fireEvent.change(nameInput, { target: { value: '数据分析师' } })
      
      const descInput = screen.getByPlaceholderText('描述这个角色的职责和工作内容...')
      fireEvent.change(descInput, { target: { value: '负责数据分析工作' } })
      
      fireEvent.click(screen.getByText('添加角色'))
      
      expect(screen.getByText('数据分析师')).toBeInTheDocument()
      expect(screen.getByText('已创建的角色 (1)')).toBeInTheDocument()
    })

    it('can add tags to custom role', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('自定义角色'))
      
      const nameInput = screen.getByPlaceholderText('例如：数据分析师')
      fireEvent.change(nameInput, { target: { value: '数据分析师' } })
      
      fireEvent.click(screen.getByText('+ 选择预设标签'))
      fireEvent.click(screen.getByText('+ 数据'))
      fireEvent.click(screen.getByText('+ 分析'))
      
      fireEvent.click(screen.getByText('添加角色'))
      
      expect(screen.getByText('数据')).toBeInTheDocument()
      expect(screen.getByText('分析')).toBeInTheDocument()
    })

    it('can remove custom role', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('自定义角色'))
      
      const nameInput = screen.getByPlaceholderText('例如：数据分析师')
      fireEvent.change(nameInput, { target: { value: '数据分析师' } })
      fireEvent.click(screen.getByText('添加角色'))
      
      expect(screen.getByText('已创建的角色 (1)')).toBeInTheDocument()
      
      fireEvent.click(screen.getAllByText('移除')[0])
      expect(screen.getByText('已创建的角色 (0)')).toBeInTheDocument()
    })
  })

  describe('Confirm Button', () => {
    it('is disabled when no agents selected', () => {
      render(<AgentConfigModal {...defaultProps} />)
      expect(screen.getByText('确认配置')).toBeDisabled()
    })

    it('is enabled when preset role selected', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('产品经理').closest('button')!)
      
      const confirmButton = screen.getByText('确认配置')
      expect(confirmButton).not.toBeDisabled()
    })

    it('is enabled when custom role created', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('自定义角色'))
      
      const nameInput = screen.getByPlaceholderText('例如：数据分析师')
      fireEvent.change(nameInput, { target: { value: '数据分析师' } })
      fireEvent.click(screen.getByText('添加角色'))
      
      const confirmButton = screen.getByText('确认配置')
      expect(confirmButton).not.toBeDisabled()
    })

    it('calls onAgentsConfigured on confirm', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('产品经理').closest('button')!)
      fireEvent.click(screen.getByText('后端开发').closest('button')!)
      
      fireEvent.click(screen.getByText('确认配置'))
      
      expect(defaultProps.onAgentsConfigured).toHaveBeenCalled()
    })

    it('closes modal after confirming', () => {
      render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('产品经理').closest('button')!)
      fireEvent.click(screen.getByText('确认配置'))
      
      expect(defaultProps.onClose).toHaveBeenCalled()
    })
  })

  describe('Reset State', () => {
    it('resets when modal is reopened', () => {
      const { rerender } = render(<AgentConfigModal {...defaultProps} />)
      
      fireEvent.click(screen.getByText('产品经理').closest('button')!)
      expect(screen.getByText('已选择 (1)')).toBeInTheDocument()
      
      rerender(<AgentConfigModal {...defaultProps} isOpen={false} />)
      rerender(<AgentConfigModal {...defaultProps} isOpen={true} />)
      
      expect(screen.getByText('已选择 (0)')).toBeInTheDocument()
    })
  })
})

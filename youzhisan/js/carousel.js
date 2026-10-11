document.addEventListener('DOMContentLoaded', function () {
  const carousel = document.querySelector('.carousel')
  const items = document.querySelectorAll('.carousel-item')
  const prevBtn = document.querySelector('.carousel-button.prev')
  const nextBtn = document.querySelector('.carousel-button.next')

  // 定义固定的移动距离
  const SLIDE_WIDTH = 400  // 每个item的宽度
  const VIEWPORT_CENTER = window.innerWidth / 2  // 视口中心点

  // 克隆节点实现无缝效果
  const firstClone = items[0].cloneNode(true)
  const secondClone = items[1].cloneNode(true)
  const lastClone = items[items.length - 1].cloneNode(true)
  const secondLastClone = items[items.length - 2].cloneNode(true)
  
  carousel.appendChild(firstClone)
  carousel.appendChild(secondClone)
  carousel.insertBefore(lastClone, items[0])
  carousel.insertBefore(secondLastClone, lastClone)

  let currentIndex = 3  // 从第三个开始，确保中间图片active
  const totalItems = items.length + 4
  let autoPlayTimer
  let isTransitioning = false

  // 计算需要的偏移量，使active项居中
  function calculateOffset(index) {
    const centerPosition = VIEWPORT_CENTER - SLIDE_WIDTH / 2
    return -(index * SLIDE_WIDTH - centerPosition + 400)  // 400是额外偏移量，根据实际情况调整
  }

  // 初始化位置
  carousel.style.transform = `translateX(${calculateOffset(currentIndex)}px)`
  updateActiveState()

  function updateActiveState() {
    const allItems = document.querySelectorAll('.carousel-item')
    allItems.forEach(item => item.classList.remove('active'))
    allItems[currentIndex].classList.add('active')
  }

  function updateCarousel(smooth = true) {
    if (smooth) {
      carousel.style.transition = 'transform 0.8s ease'
    } else {
      carousel.style.transition = 'none'
    }
    carousel.style.transform = `translateX(${calculateOffset(currentIndex)}px)`
    updateActiveState()
  }

  function handleTransitionEnd() {
    if (currentIndex <= 1) {
      currentIndex = items.length + 1
      updateCarousel(false)
    } else if (currentIndex >= totalItems - 2) {
      currentIndex = 2
      updateCarousel(false)
    }
    isTransitioning = false
  }

  function nextSlide() {
    if (isTransitioning) return
    isTransitioning = true
    currentIndex++
    updateCarousel()
  }

  function prevSlide() {
    if (isTransitioning) return
    isTransitioning = true
    currentIndex--
    updateCarousel()
  }

  // 自动播放
  function startAutoPlay() {
    autoPlayTimer = setInterval(nextSlide, 4000)
  }

  function stopAutoPlay() {
    clearInterval(autoPlayTimer)
  }

  // 事件监听
  carousel.addEventListener('transitionend', handleTransitionEnd)

  prevBtn.addEventListener('click', () => {
    stopAutoPlay()
    prevSlide()
    startAutoPlay()
  })

  nextBtn.addEventListener('click', () => {
    stopAutoPlay()
    nextSlide()
    startAutoPlay()
  })

  // 鼠标悬停控制
  const carouselContainer = document.querySelector('.carousel-container')
  carouselContainer.addEventListener('mouseenter', stopAutoPlay)
  carouselContainer.addEventListener('mouseleave', startAutoPlay)

  // 触摸事件支持
  let touchStartX = 0
  let touchEndX = 0

  carousel.addEventListener('touchstart', (e) => {
    touchStartX = e.touches[0].clientX
    stopAutoPlay()
  })

  carousel.addEventListener('touchmove', (e) => {
    touchEndX = e.touches[0].clientX
  })

  carousel.addEventListener('touchend', () => {
    const difference = touchStartX - touchEndX
    if (Math.abs(difference) > 50) {
      if (difference > 0) {
        nextSlide()
      } else {
        prevSlide()
      }
    }
    startAutoPlay()
  })

  // 启动自动播放
  startAutoPlay()
})

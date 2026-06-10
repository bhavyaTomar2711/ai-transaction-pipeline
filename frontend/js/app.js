/**
 * AI Transaction Pipeline — Frontend Application
 * Handles CSV upload, job polling, results display
 */

class TransactionApp {
  constructor() {
    this.currentJobId = null;
    this.currentResults = null;
    this.statusPollInterval = null;
    this.allTransactions = [];
    this.filteredTransactions = [];
    this.currentPage = 1;
    this.pageSize = 10;
    this.sortColumn = 'date';
    this.sortDirection = 'desc';
    this.currentFilter = 'all';
    this.searchTerm = '';

    this.initEventListeners();
    this.loadJobs();
  }

  initEventListeners() {
    // Upload zone drag-drop
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    uploadZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadZone.style.backgroundColor = 'rgba(10, 132, 255, 0.1)';
      uploadZone.style.borderColor = 'var(--accent-blue)';
    });

    uploadZone.addEventListener('dragleave', () => {
      uploadZone.style.backgroundColor = '';
      uploadZone.style.borderColor = '';
    });

    uploadZone.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadZone.style.backgroundColor = '';
      uploadZone.style.borderColor = '';

      if (e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (file.name.endsWith('.csv')) {
          this.handleFileUpload(file);
        } else {
          this.showToast('Please drop a CSV file', 'error');
        }
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        this.handleFileUpload(e.target.files[0]);
      }
    });

    // Make upload zone clickable
    uploadZone.addEventListener('click', () => {
      fileInput.click();
    });
  }

  async handleFileUpload(file) {
    if (!file.name.endsWith('.csv')) {
      this.showToast('Only CSV files are supported', 'error');
      return;
    }

    // Show progress
    const progressContainer = document.getElementById('uploadProgress');
    progressContainer.style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/jobs/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }

      const data = await response.json();
      this.currentJobId = data.job_id;

      this.showToast(`File uploaded: ${file.name}`, 'success');
      this.showProcessingView();
      this.startStatusPolling();
    } catch (error) {
      this.showToast(`Upload failed: ${error.message}`, 'error');
      progressContainer.style.display = 'none';
    }
  }

  startStatusPolling() {
    // Clear any existing interval
    if (this.statusPollInterval) {
      clearInterval(this.statusPollInterval);
    }

    // Poll every 2 seconds
    this.statusPollInterval = setInterval(() => {
      this.checkJobStatus();
    }, 2000);

    // Check immediately
    this.checkJobStatus();
  }

  async checkJobStatus() {
    if (!this.currentJobId) return;

    try {
      const response = await fetch(`/api/jobs/${this.currentJobId}/status`);
      if (!response.ok) {
        throw new Error('Failed to fetch job status');
      }

      const data = await response.json();
      this.updateProcessingSteps(data.status);

      if (data.status === 'completed') {
        clearInterval(this.statusPollInterval);
        this.statusPollInterval = null;

        // Fetch full results
        await this.loadJobResults(this.currentJobId);
        this.showResultsView();
      } else if (data.status === 'failed') {
        clearInterval(this.statusPollInterval);
        this.statusPollInterval = null;

        this.showToast(`Job failed: ${data.error_message}`, 'error');
        this.showDashboard();
      }
    } catch (error) {
      console.error('Status poll error:', error);
    }
  }

  updateProcessingSteps(status) {
    const steps = ['upload', 'clean', 'anomaly', 'classify', 'summary'];
    const statusMap = {
      pending: 0,
      uploading: 1,
      cleaning: 2,
      detecting_anomalies: 3,
      classifying: 4,
      summarizing: 5,
      completed: 5,
    };

    const currentStep = statusMap[status] || 0;

    steps.forEach((step, index) => {
      const stepEl = document.getElementById(`step-${step}`);
      if (index < currentStep) {
        stepEl.classList.add('completed');
      } else if (index === currentStep) {
        stepEl.classList.add('active');
      } else {
        stepEl.classList.remove('completed', 'active');
      }
    });
  }

  async loadJobResults(jobId) {
    try {
      const response = await fetch(`/api/jobs/${jobId}/results`);
      if (!response.ok) {
        throw new Error('Failed to fetch results');
      }

      const data = await response.json();
      this.currentResults = data;
      this.allTransactions = data.transactions || [];
      this.filteredTransactions = [...this.allTransactions];
      this.renderResults();
    } catch (error) {
      this.showToast(`Error loading results: ${error.message}`, 'error');
    }
  }

  renderResults() {
    if (!this.currentResults) return;

    const summary = this.currentResults.summary;

    // Render stats grid
    const statsGrid = document.getElementById('statsGrid');
    statsGrid.innerHTML = `
      <div class="stat-card">
        <div class="stat-label">Total Transactions</div>
        <div class="stat-value">${this.allTransactions.length}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Spend (INR)</div>
        <div class="stat-value">₹${(summary.total_spend_inr || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Spend (USD)</div>
        <div class="stat-value">$${(summary.total_spend_usd || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">⚠ Anomalies</div>
        <div class="stat-value" style="color: var(--accent-red);">${summary.anomaly_count || 0}</div>
      </div>
    `;

    // Render narrative
    if (summary.narrative) {
      const narrativeCard = document.getElementById('narrativeCard');
      narrativeCard.style.display = 'block';
      document.getElementById('narrativeText').textContent = summary.narrative;

      const riskBadge = document.getElementById('riskBadge');
      const riskColor = summary.risk_level === 'HIGH' ? 'var(--accent-red)' :
                       summary.risk_level === 'MEDIUM' ? 'var(--accent-orange)' :
                       'var(--accent-green)';
      riskBadge.innerHTML = `
        <span style="display: inline-block; padding: 4px 12px; background: ${riskColor}20; color: ${riskColor}; border-radius: 16px; font-size: var(--font-size-sm); margin-top: 12px;">
          Risk Level: ${summary.risk_level}
        </span>
      `;
    }

    // Render charts
    this.renderCategoryChart(summary.category_breakdown || {});
    this.renderMerchantChart(summary.top_merchants || []);

    // Render transactions table
    this.renderTransactionsTable();
  }

  renderCategoryChart(categoryBreakdown) {
    const container = document.getElementById('categoryChart');
    const categories = Object.entries(categoryBreakdown);

    if (categories.length === 0) {
      container.innerHTML = '<p style="text-align: center; color: var(--text-tertiary);">No data</p>';
      return;
    }

    const total = categories.reduce((sum, [_, value]) => sum + value, 0);
    const colors = ['#0A84FF', '#30D158', '#FF9F0A', '#FF453A', '#BF5AF2', '#64D2FF'];

    let svg = '<svg viewBox="0 0 200 200" style="width: 100%; max-width: 200px; height: 200px;">';
    let currentAngle = -90;

    categories.forEach(([category, amount], index) => {
      const percentage = (amount / total) * 100;
      const sliceAngle = (percentage / 100) * 360;
      const radius = 80;

      const startRad = (currentAngle * Math.PI) / 180;
      const endRad = ((currentAngle + sliceAngle) * Math.PI) / 180;

      const x1 = 100 + radius * Math.cos(startRad);
      const y1 = 100 + radius * Math.sin(startRad);
      const x2 = 100 + radius * Math.cos(endRad);
      const y2 = 100 + radius * Math.sin(endRad);

      const largeArc = sliceAngle > 180 ? 1 : 0;

      const pathData = `M 100 100 L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;
      svg += `<path d="${pathData}" fill="${colors[index % colors.length]}" opacity="0.8" stroke="var(--bg-primary)" stroke-width="2"/>`;

      currentAngle += sliceAngle;
    });

    svg += '</svg>';
    container.innerHTML = svg;

    // Add legend
    const legend = categories
      .map(([category, amount], index) => `
        <div style="display: flex; align-items: center; gap: 8px; margin: 8px 0; font-size: var(--font-size-sm);">
          <div style="width: 12px; height: 12px; background: ${colors[index % colors.length]}; border-radius: 2px;"></div>
          <span>${category}: ₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
        </div>
      `)
      .join('');

    container.innerHTML += `<div style="margin-top: 16px; text-align: left;">${legend}</div>`;
  }

  renderMerchantChart(topMerchants) {
    const container = document.getElementById('merchantChart');

    if (!topMerchants || topMerchants.length === 0) {
      container.innerHTML = '<p style="text-align: center; color: var(--text-tertiary);">No data</p>';
      return;
    }

    const maxAmount = Math.max(...topMerchants.map(m => m.amount));

    const html = topMerchants
      .slice(0, 5)
      .map((merchant) => {
        const percentage = (merchant.amount / maxAmount) * 100;
        return `
          <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
              <span style="font-size: var(--font-size-sm); color: var(--text-secondary);">${merchant.merchant}</span>
              <span style="font-size: var(--font-size-sm); color: var(--text-primary);">₹${merchant.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
            </div>
            <div style="background: rgba(10, 132, 255, 0.1); border-radius: 4px; height: 6px; overflow: hidden;">
              <div style="background: var(--accent-blue); height: 100%; width: ${percentage}%; border-radius: 4px;"></div>
            </div>
          </div>
        `;
      })
      .join('');

    container.innerHTML = html;
  }

  renderTransactionsTable() {
    const tableBody = document.getElementById('tableBody');

    if (this.filteredTransactions.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 32px; color: var(--text-tertiary);">
            No transactions match your filter
          </td>
        </tr>
      `;
      return;
    }

    const startIdx = (this.currentPage - 1) * this.pageSize;
    const endIdx = startIdx + this.pageSize;
    const pageTransactions = this.filteredTransactions.slice(startIdx, endIdx);

    tableBody.innerHTML = pageTransactions
      .map((txn) => {
        const anomalyClass = txn.is_anomaly ? 'style="color: var(--accent-red);"' : '';
        const flags = txn.is_anomaly ? '⚠ Anomaly' : '';

        return `
          <tr>
            <td>${txn.txn_id}</td>
            <td>${new Date(txn.date).toLocaleDateString()}</td>
            <td>${txn.merchant}</td>
            <td>${txn.amount}</td>
            <td>${txn.currency}</td>
            <td>
              <span style="background: ${txn.status === 'completed' ? 'var(--status-completed-bg)' : 'var(--status-pending-bg)'}; color: ${txn.status === 'completed' ? 'var(--accent-green)' : 'var(--accent-orange)'}; padding: 4px 8px; border-radius: 4px; font-size: var(--font-size-sm);">
                ${txn.status}
              </span>
            </td>
            <td>${txn.category || 'Uncategorized'}</td>
            <td ${anomalyClass}>${flags}</td>
          </tr>
        `;
      })
      .join('');

    // Render pagination
    this.renderPagination();
  }

  renderPagination() {
    const totalPages = Math.ceil(this.filteredTransactions.length / this.pageSize);
    const paginationInfo = document.getElementById('paginationInfo');
    const startIdx = (this.currentPage - 1) * this.pageSize + 1;
    const endIdx = Math.min(this.currentPage * this.pageSize, this.filteredTransactions.length);

    paginationInfo.textContent = `Showing ${startIdx} to ${endIdx} of ${this.filteredTransactions.length}`;

    const paginationBtns = document.getElementById('paginationBtns');
    paginationBtns.innerHTML = '';

    for (let i = 1; i <= totalPages; i++) {
      const btn = document.createElement('button');
      btn.className = `filter-btn ${i === this.currentPage ? 'active' : ''}`;
      btn.textContent = i;
      btn.onclick = () => {
        this.currentPage = i;
        this.renderTransactionsTable();
      };
      paginationBtns.appendChild(btn);
    }
  }

  searchTransactions(term) {
    this.searchTerm = term.toLowerCase();
    this.applyFilters();
  }

  filterTransactions(filter) {
    this.currentFilter = filter;
    this.applyFilters();
  }

  applyFilters() {
    this.filteredTransactions = this.allTransactions.filter((txn) => {
      // Apply status filter
      if (this.currentFilter === 'anomalies' && !txn.is_anomaly) {
        return false;
      }

      // Apply search term
      if (this.searchTerm) {
        const searchableFields = [
          txn.txn_id,
          txn.merchant,
          txn.category,
          txn.amount.toString(),
          txn.currency,
        ];
        if (!searchableFields.some((field) => field.toLowerCase().includes(this.searchTerm))) {
          return false;
        }
      }

      return true;
    });

    this.currentPage = 1;
    this.renderTransactionsTable();
  }

  sortTable(column) {
    if (this.sortColumn === column) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
    } else {
      this.sortColumn = column;
      this.sortDirection = 'desc';
    }

    this.filteredTransactions.sort((a, b) => {
      let aVal = a[column];
      let bVal = b[column];

      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (this.sortDirection === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    this.renderTransactionsTable();
  }

  async loadJobs() {
    try {
      const response = await fetch('/api/jobs');
      if (!response.ok) {
        console.error('Failed to load jobs');
        return;
      }

      const data = await response.json();
      // The endpoint returns an array directly
      this.renderJobsList(Array.isArray(data) ? data : data.jobs || []);
    } catch (error) {
      console.error('Error loading jobs:', error);
    }
  }

  renderJobsList(jobs) {
    const jobsList = document.getElementById('jobsList');
    const jobCount = document.getElementById('jobCount');

    jobCount.textContent = `${jobs.length} job${jobs.length !== 1 ? 's' : ''}`;

    if (jobs.length === 0) {
      jobsList.innerHTML = '<p style="text-align: center; color: var(--text-tertiary); padding: 32px;">No jobs yet. Upload a CSV to get started!</p>';
      return;
    }

    jobsList.innerHTML = jobs
      .map((job) => {
        const statusColor = {
          pending: 'var(--status-pending)',
          processing: 'var(--status-processing)',
          completed: 'var(--status-completed)',
          failed: 'var(--status-failed)',
        }[job.status] || 'var(--text-tertiary)';

        return `
          <div class="job-item" style="cursor: pointer;" onclick="app.viewJob('${job.id}')">
            <div style="flex: 1;">
              <div style="font-weight: 600; color: var(--text-primary);">${job.filename}</div>
              <div style="font-size: var(--font-size-sm); color: var(--text-secondary); margin-top: 4px;">
                ${new Date(job.created_at).toLocaleString()}
              </div>
            </div>
            <div style="text-align: right;">
              <div style="background: ${statusColor}20; color: ${statusColor}; padding: 4px 12px; border-radius: 16px; font-size: var(--font-size-sm); margin-bottom: 8px;">
                ${job.status}
              </div>
              <div style="font-size: var(--font-size-sm); color: var(--text-tertiary);">
                ${job.row_count_clean || 0} rows
              </div>
            </div>
          </div>
        `;
      })
      .join('');
  }

  async viewJob(jobId) {
    this.currentJobId = jobId;
    await this.loadJobResults(jobId);
    this.showResultsView();
  }

  showDashboard() {
    document.getElementById('dashboardView').style.display = 'block';
    document.getElementById('processingView').style.display = 'none';
    document.getElementById('resultsView').style.display = 'none';
    this.loadJobs();
  }

  showProcessingView() {
    document.getElementById('dashboardView').style.display = 'none';
    document.getElementById('processingView').style.display = 'block';
    document.getElementById('resultsView').style.display = 'none';
  }

  showResultsView() {
    document.getElementById('dashboardView').style.display = 'none';
    document.getElementById('processingView').style.display = 'none';
    document.getElementById('resultsView').style.display = 'block';
  }

  filterJobs(status) {
    // Update filter UI
    document.querySelectorAll('.table-filters .filter-btn').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.status === status);
    });

    // Reload with filter (would need backend support)
    this.loadJobs();
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    toast.style.cssText = `
      background: ${type === 'error' ? 'var(--accent-red)' : type === 'success' ? 'var(--accent-green)' : 'var(--accent-blue)'};
      color: white;
      padding: 12px 16px;
      border-radius: var(--radius-md);
      margin: 8px;
      animation: slideInUp 0.3s var(--ease-out);
      box-shadow: var(--shadow-lg);
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.animation = 'slideOutDown 0.3s var(--ease-out)';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new TransactionApp();
});

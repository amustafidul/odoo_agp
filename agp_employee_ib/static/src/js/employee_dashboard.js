odoo.define("agp_employee_ib.EmployeeDashboard", function (require) {
  "use strict";

  var AbstractAction = require("web.AbstractAction");
  var core = require("web.core");
  var rpc = require("web.rpc");

  if (typeof ChartDataLabels !== "undefined") {
    Chart.register(ChartDataLabels);
  }

  var DashBoard = AbstractAction.extend({
    contentTemplate: "agp_employee_ib.EmployeeDashboardTemplate",

    ageGroupChart: null,
    genderChart: null,
    educationChart: null,

    summaryData: [],

    //----------------------------------------------------------------------
    // START
    //----------------------------------------------------------------------
    start: function () {
      this._super.apply(this, arguments);
      this._populateBranchSelect();
      this._setupFilterListeners();
      this._renderChartsWithDelay();
    },

    //----------------------------------------------------------------------
    // FILTER: Branch & Employment Type
    //----------------------------------------------------------------------
    _populateBranchSelect: function () {
      var self = this;
      rpc
        .query({
          model: "hr.branch",
          method: "search_read",
          fields: ["id", "name"],
        })
        .then(function (branches) {
          var $branchSelect = self.$el.find("#branchSelect");
          branches.forEach(function (branch) {
            $branchSelect.append(new Option(branch.name, branch.id));
          });
        });
    },

    _setupFilterListeners: function () {
      var self = this;
      this.$el
        .find("#employmentTypeSelect, #branchSelect")
        .on("change", function () {
          self._applyFilters();
        });
    },

    _applyFilters: function () {
      const employmentType = this.$el.find("#employmentTypeSelect").val();
      const branchId = this.$el.find("#branchSelect").val();
      console.log("Filter => Employment Type:", employmentType, ", Branch:", branchId);
      this._renderChartsWithDelay(employmentType, branchId);
    },

    //----------------------------------------------------------------------
    // RENDER CHARTS & TABEL SUMMARY
    //----------------------------------------------------------------------
    _renderChartsWithDelay: function (employmentType = null, branchId = null) {
      var self = this;

      this.$el.find("#loadingOverlay").show();
      this.$el.find("#dashboardContent").hide();

      this._fetchAgeGroups().then(function (ageGroups) {
        Promise.all([
          self._fetchGenderData(employmentType, branchId),
          self._fetchAgeGroupData(employmentType, branchId), // data chart age
          self._fetchEducationLevelData(employmentType, branchId),
          self._fetchSummaryData(employmentType, branchId, ageGroups),
        ]).then(function (results) {
          const [genderData, ageGroupChartData, educationData, summaryData] = results;
          self.renderCharts(genderData, ageGroupChartData, educationData);
          self._renderSummaryTable(summaryData, ageGroups);

          setTimeout(function () {
            self.$el.find("#loadingOverlay").hide();
            self.$el.find("#dashboardContent").show();
          }, 1000);
        });
      });
    },

    //----------------------------------------------------------------------
    // FETCH DATA UNTUK CHART
    //----------------------------------------------------------------------
    _fetchGenderData: function (employmentType, branchId) {
      let domain = [];
      if (employmentType) domain.push(["employment_type", "=", employmentType]);
      if (branchId) domain.push(["hr_branch_id", "=", parseInt(branchId)]);

      return this._rpc({
        model: "hr.employee",
        method: "read_group",
        domain: domain,
        fields: ["gender"],
        groupBy: ["gender"],
      }).then(function (result) {
        var genderData = {
          labels: ["Laki-laki", "Perempuan"],
          male: 0,
          female: 0,
        };

        if (result.length === 0) {
          return genderData;
        }

        result.forEach(function (group) {
          if (group.gender === "male") {
            genderData.male = group.gender_count || 0;
          } else if (group.gender === "female") {
            genderData.female = group.gender_count || 0;
          }
        });

        return genderData;
      });
    },

    _fetchAgeGroupData: function (employmentType, branchId) {
      let domain = [];
      if (employmentType) domain.push(["employment_type", "=", employmentType]);
      if (branchId) domain.push(["hr_branch_id", "=", parseInt(branchId)]);

      return this._rpc({
        model: "hr.employee",
        method: "read_group",
        domain: domain,
        fields: ["kelompok_umur_id"],
        groupBy: ["kelompok_umur_id"],
      }).then(function (result) {
        var ageGroupData = { labels: [], counts: [] };
        if (result.length === 0) {
          ageGroupData.labels.push("Tidak ada data kelompok umur yang ditemukan");
          ageGroupData.counts.push(0);
        } else {
          result.forEach(function (group) {
            ageGroupData.labels.push(group.kelompok_umur_id[1]);
            ageGroupData.counts.push(group.kelompok_umur_id_count);
          });
        }
        return ageGroupData;
      });
    },

    _fetchEducationLevelData: function (employmentType, branchId) {
      let domain = [];
      if (employmentType) domain.push(["employment_type", "=", employmentType]);
      if (branchId) domain.push(["hr_branch_id", "=", parseInt(branchId)]);

      return this._rpc({
        model: "hr.employee",
        method: "search_read",
        domain: domain,
        fields: ["id", "hr_employee_ijazah_ids"],
      }).then((employees) => {
        var educationCounts = {
          sd: 0,
          smp: 0,
          sma: 0,
          d1: 0,
          d2: 0,
          d3: 0,
          d4: 0,
          s1: 0,
          s2: 0,
          s3: 0,
        };

        let allIjazahIds = [];
        employees.forEach((emp) => {
          if (emp.hr_employee_ijazah_ids && emp.hr_employee_ijazah_ids.length) {
            allIjazahIds = allIjazahIds.concat(emp.hr_employee_ijazah_ids);
          }
        });

        if (!allIjazahIds.length) {
          return educationCounts;
        }

        let uniqueIjazahIds = [...new Set(allIjazahIds)];

        return rpc
          .query({
            model: "hr.employee.ijazah",
            method: "search_read",
            domain: [["id", "in", uniqueIjazahIds]],
            fields: ["pendidikan_terakhir_selc"],
          })
          .then(function (ijazahs) {
            ijazahs.forEach((ij) => {
              let p = ij.pendidikan_terakhir_selc;
              if (p && educationCounts.hasOwnProperty(p)) {
                educationCounts[p]++;
              }
            });
            return educationCounts;
          });
      });
    },

    //----------------------------------------------------------------------
    // FETCH DATA KELOMPOK UMUR (model hr.employee.kelompok.umur)
    //----------------------------------------------------------------------
    _fetchAgeGroups: function () {
      return rpc.query({
        model: "hr.employee.kelompok.umur",
        method: "search_read",
        domain: [],
        fields: ["id", "name", "min_age", "max_age"],
        order: "min_age",
      });
    },

    //----------------------------------------------------------------------
    // FETCH DATA UNTUK TABEL SUMMARY
    //----------------------------------------------------------------------
    _fetchSummaryData: function (employmentType, branchId, ageGroups) {
      let domain = [];
      if (employmentType) domain.push(["employment_type", "=", employmentType]);
      if (branchId) domain.push(["hr_branch_id", "=", parseInt(branchId)]);

      return this._rpc({
        model: "hr.employee",
        method: "search_read",
        domain: domain,
        fields: [
          "id",
          "name",
          "gender",
          "employment_type",
          "hr_branch_id",
          "kelompok_umur_id",
          "hr_employee_ijazah_ids",
        ],
      }).then((employees) => {
        let summaryMap = {};

        let initRow = (etype) => {
          let row = {
            keterangan: etype,
            employee_ids: new Set(),
            male: 0,
            female: 0,
            sd: 0,
            smp: 0,
            sma: 0,
            d1: 0,
            d2: 0,
            d3: 0,
            d4: 0,
            s1: 0,
            s2: 0,
            s3: 0,
            total: 0,
            age_groups: {},
          };
          // Counter Kelompok Umur
          ageGroups.forEach((ag) => {
            row.age_groups[ag.id] = 0;
          });
          return row;
        };

        let allIjazahIds = [];
        employees.forEach((emp) => {
          let etype = emp.employment_type || "Undefined (Employee Type is not set)";
          if (!summaryMap[etype]) {
            summaryMap[etype] = initRow(etype);
          }
          let row = summaryMap[etype];

          row.employee_ids.add(emp.id);

          // Gender
          if (emp.gender === "male") row.male++;
          if (emp.gender === "female") row.female++;

          // Kelompok Umur (M2O)
          if (emp.kelompok_umur_id) {
            let groupId = emp.kelompok_umur_id[0];
            if (row.age_groups[groupId] !== undefined) {
              row.age_groups[groupId]++;
            }
          }

          // Kumpulkan ijazah
          if (emp.hr_employee_ijazah_ids && emp.hr_employee_ijazah_ids.length) {
            allIjazahIds = allIjazahIds.concat(emp.hr_employee_ijazah_ids);
          }
        });

        let uniqueIjazahIds = [...new Set(allIjazahIds)];
        if (!uniqueIjazahIds.length) {
          Object.values(summaryMap).forEach((r) => {
            r.total = r.employee_ids.size;
          });
          return Object.values(summaryMap);
        }

        return rpc
          .query({
            model: "hr.employee.ijazah",
            method: "search_read",
            domain: [["id", "in", uniqueIjazahIds]],
            fields: ["pendidikan_terakhir_selc", "employee_id"],
          })
          .then(function (ijazahs) {
            let empEduMap = {};
            ijazahs.forEach((ij) => {
              let empId = ij.employee_id[0]; // M2O field
              if (!empEduMap[empId]) {
                empEduMap[empId] = [];
              }
              empEduMap[empId].push(ij.pendidikan_terakhir_selc);
            });

            Object.keys(summaryMap).forEach((etype) => {
              let row = summaryMap[etype];
              row.employee_ids.forEach((empId) => {
                let pendArray = empEduMap[empId] || [];
                pendArray.forEach((p) => {
                  if (p && row.hasOwnProperty(p)) {
                    row[p]++;
                  }
                });
              });

              row.total = row.employee_ids.size;
            });

            return Object.values(summaryMap);
          });
      });
    },

    //----------------------------------------------------------------------
    // RENDER TABEL SUMMARY (scroll horizontal + uppercase keterangan)
    //----------------------------------------------------------------------
    _renderSummaryTable: function (data, ageGroups) {
      this.summaryData = data || [];
      let $thead = this.$el.find("#summaryTable thead");
      let $tbody = this.$el.find("#summaryTable tbody");
      $thead.empty();
      $tbody.empty();

      // Header
      let headerHtml = `<tr>
                <th rowspan="2" style="text-align: center; vertical-align: middle;">KETERANGAN</th>
                <th colspan="2" style="text-align: center; vertical-align: middle;">JENIS KELAMIN</th>
                <th colspan="${ageGroups.length}" style="text-align: center; vertical-align: middle;">KELOMPOK UMUR</th>
                <th colspan="8" style="text-align: center; vertical-align: middle;">PENDIDIKAN</th>
                <th rowspan="2" style="text-align: center; vertical-align: middle;">TOTAL EMPLOYEE</th>
            </tr>`;
      headerHtml += `<tr>
                <th style="text-align: center;">L</th>
                <th style="text-align: center;">P</th>`;
      ageGroups.forEach((ag) => {
        headerHtml += `<th style="text-align: center;">${ag.name}</th>`;
      });
      headerHtml += `
                <th style="text-align: center;">SD</th>
                <th style="text-align: center;">SMP</th>
                <th style="text-align: center;">SMA</th>
                <th style="text-align: center;">D3</th>
                <th style="text-align: center;">D4</th>
                <th style="text-align: center;">S1</th>
                <th style="text-align: center;">S2</th>
                <th style="text-align: center;">S3</th>
            </tr>`;
      $thead.html(headerHtml);

      // Body
      this.summaryData.forEach((row) => {
        let keterangan = row.keterangan;
        // Uppercase selain Undefined
        if (keterangan.toLowerCase().indexOf("undefined") === -1) {
          keterangan = keterangan.toUpperCase();
        }
        let rowHtml = `<tr style="cursor: pointer;">
                    <td style="text-align: center;">${keterangan}</td>
                    <td style="text-align: center;">${row.male}</td>
                    <td style="text-align: center;">${row.female}</td>`;
        ageGroups.forEach((ag) => {
          let val = row.age_groups[ag.id] || 0;
          rowHtml += `<td style="text-align: center;">${val}</td>`;
        });
        rowHtml += `
                    <td style="text-align: center;">${row.sd}</td>
                    <td style="text-align: center;">${row.smp}</td>
                    <td style="text-align: center;">${row.sma}</td>
                    <td style="text-align: center;">${row.d3}</td>
                    <td style="text-align: center;">${row.d4}</td>
                    <td style="text-align: center;">${row.s1}</td>
                    <td style="text-align: center;">${row.s2}</td>
                    <td style="text-align: center;">${row.s3}</td>
                    <td style="text-align: center;">${row.total}</td>
                </tr>`;
        let $tr = $(rowHtml);

        // Klik => buka detail (domain gabungan: etype + filter)
        $tr.on("click", () => {
          this._showDetail(row.keterangan);
        });
        $tbody.append($tr);
      });
    },

    //----------------------------------------------------------------------
    // MENAMPILKAN DETAIL (TREE VIEW) KARYAWAN
    // Filter: row keterangan (etype) + controller (empType, branch)
    //----------------------------------------------------------------------
    _showDetail: function (etype) {
      let ctrlEmpType = this.$el.find("#employmentTypeSelect").val();
      let ctrlBranch = this.$el.find("#branchSelect").val();

      // Pastikan domain tidak tumpang tindih
      let domain = [];
      // Etype "Undefined (Employee Type is not set)" artinya employment_type = False
      if (etype.indexOf("Undefined") !== -1) {
        domain.push(["employment_type", "=", false]);
      } else {
        domain.push(["employment_type", "=", etype.toLowerCase()]);
      }

      if (ctrlBranch) {
        domain.push(["hr_branch_id", "=", parseInt(ctrlBranch)]);
      }
      if (ctrlEmpType) {
        // kalau user men-set filter global, let's combine
        domain.push(["employment_type", "=", ctrlEmpType]);
      }

      this.do_action({
        type: "ir.actions.act_window",
        name: "Detail Employees",
        res_model: "hr.employee",
        domain: domain,
        views: [
          [false, "list"],
          [false, "form"],
        ],
        target: "current",
      });
    },

    //----------------------------------------------------------------------
    // RENDER CHART (Kelompok Umur, Jenis Kelamin, Pendidikan) + Bold Datalabels
    //----------------------------------------------------------------------
    renderCharts: function (genderData, ageGroupData, educationData) {
      const ageGroupChartCanvas = this.$el.find("#ageGroupChart")[0];
      const genderChartCanvas = this.$el.find("#genderChart")[0];
      const educationChartCanvas = this.$el.find("#educationChart")[0];

      if (!ageGroupChartCanvas || !genderChartCanvas || !educationChartCanvas) {
        console.error("Canvas elements not found.");
        return;
      }

      // Destroy old charts if exist
      if (this.ageGroupChart) this.ageGroupChart.destroy();
      if (this.genderChart) this.genderChart.destroy();
      if (this.educationChart) this.educationChart.destroy();

      // Chart Kelompok Umur (Pie)
      this.ageGroupChart = new Chart(ageGroupChartCanvas.getContext("2d"), {
        type: "pie",
        data: {
          labels: ageGroupData.labels,
          datasets: [
            {
              label: "Kelompok Umur",
              data: ageGroupData.counts,
              backgroundColor: this._getDynamicColors(ageGroupData.labels.length),
            },
          ],
        },
        options: {
          animation: { duration: 1500, easing: "easeOutBounce" },
          plugins: {
            tooltip: { enabled: true },
            datalabels: {
              display: true,
              color: "#fff",
              font: { weight: "bold" },
              formatter: function (value, ctx) {
                let dataset = ctx.chart.data.datasets[0];
                let sum = dataset.data.reduce((a, b) => a + b, 0);
                let percentage = ((value / sum) * 100).toFixed(2) + "%";
                return percentage;
              },
            },
          },
        },
      });

      // Chart Jenis Kelamin (Doughnut)
      // Pastikan data [genderData.male, genderData.female] sesuai label
      let genderValues = [genderData.male, genderData.female];

      this.genderChart = new Chart(genderChartCanvas.getContext("2d"), {
        type: "doughnut",
        data: {
          labels: genderData.labels,
          datasets: [
            {
              label: "Jenis Kelamin",
              data: genderValues,
              backgroundColor: ["#36A2EB", "#FF6384"],
            },
          ],
        },
        options: {
          animation: { duration: 1500, easing: "easeOutBounce" },
          plugins: {
            tooltip: { enabled: true },
            datalabels: {
              display: true,
              color: "#fff",
              font: { weight: "bold" },
              formatter: function (value, ctx) {
                let dataset = ctx.chart.data.datasets[0];
                let sum = dataset.data.reduce((a, b) => a + b, 0);
                let percentage = ((value / sum) * 100).toFixed(2) + "%";
                return percentage;
              },
            },
          },
        },
      });

      // Chart Pendidikan (Bar)
      this.educationChart = new Chart(educationChartCanvas.getContext("2d"), {
        type: "bar",
        data: {
          labels: ["SD", "SMP", "SMA", "D1", "D2", "D3", "D4", "S1", "S2", "S3"],
          datasets: [
            {
              label: "Pendidikan",
              data: [
                educationData.sd,
                educationData.smp,
                educationData.sma,
                educationData.d1,
                educationData.d2,
                educationData.d3,
                educationData.d4,
                educationData.s1,
                educationData.s2,
                educationData.s3,
              ],
              backgroundColor: this._getDynamicColors(
                Object.keys(educationData).length
              ),
              borderColor: "#FFFFFF",
              borderWidth: 1,
            },
          ],
        },
        options: {
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, precision: 0 },
              title: {
                display: true,
                text: "Jumlah Karyawan",
                color: "#666",
                font: { family: "Arial", size: 12, weight: "bold" },
              },
            },
            x: {
              title: {
                display: true,
                text: "Tingkat Pendidikan",
                color: "#666",
                font: { family: "Arial", size: 12, weight: "bold" },
              },
            },
          },
          plugins: {
            legend: {
              display: true,
              labels: { color: "#666", font: { family: "Arial", size: 12 } },
            },
            tooltip: {
              enabled: true,
              callbacks: {
                label: function (context) {
                  return "Jumlah: " + context.parsed.y;
                },
              },
            },
            datalabels: {
              display: true,
              color: "#fff",
              font: { weight: "bold" },
              formatter: function (value, ctx) {
                let dataset = ctx.chart.data.datasets[0];
                let sum = dataset.data.reduce((a, b) => a + b, 0);
                let percentage = ((value / sum) * 100).toFixed(2) + "%";
                return percentage;
              },
            },
          },
        },
      });
    },

    //----------------------------------------------------------------------
    // UTIL: Warna Dinamis
    //----------------------------------------------------------------------
    _getDynamicColors: function (length) {
      const colors = [
        "#FF6384",
        "#36A2EB",
        "#FFCE56",
        "#4BC0C0",
        "#FF9F40",
        "#AA64E2",
        "#42F497",
        "#FFD700",
        "#FF6F61",
        "#F5A623",
      ];
      const result = [];
      for (let i = 0; i < length; i++) {
        result.push(colors[i % colors.length]);
      }
      return result;
    },
  });

  core.action_registry.add("employee_dashboard", DashBoard);
  return DashBoard;
});
$(document).ready(function() {
    $("select[name='page_type']").change(function() {
        this.form.submit();
    });
});

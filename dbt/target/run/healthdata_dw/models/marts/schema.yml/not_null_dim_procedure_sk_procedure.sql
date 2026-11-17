select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
    



select sk_procedure
from "healthdata_dw"."dw_gold"."dim_procedure"
where sk_procedure is null



      
    ) dbt_internal_test